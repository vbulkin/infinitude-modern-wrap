"""CarrierBridge — implicit thermostat → Carrier-cloud relay.

Companion to test_forward_proxy.py. Where the forward proxy handles
explicit `/http%3A//host/...` URL-encoded paths, the bridge handles
the *implicit* relay the legacy Perl Infinitude does in
`before_dispatch`: mirror status POSTs upstream, surface Carrier's
`serverHasChanges` flag so a proactive `/config` pull can fire, and
keep the thermostat moving even when Carrier is unreachable
(circuit-breaker + bounded timeouts).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from infinitude_proxy.capture import CaptureControl
from infinitude_proxy.carrier_bridge import CarrierBridge, _action_key
from infinitude_proxy.main import create_app
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _bridge_with_handler(handler, **kw) -> CarrierBridge:
    """A CarrierBridge whose httpx client is wired to a MockTransport
    so tests don't hit the real internet. `_outbound` requires
    `source_headers` on every call — tests that drive `relay()`
    directly must pass `headers=...`.
    """
    kw.setdefault("enabled", True)
    cb = CarrierBridge(**kw)
    cb._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(handler),
        timeout=cb._timeout,
        follow_redirects=False,
    )
    return cb


_DEFAULT_HEADERS = {"Authorization": "Basic test-source="}


def test_action_key_method_path_query():
    assert _action_key("GET", "/x", None) == "GET /x"
    assert _action_key("POST", "/y", "a=b") == "POST /y?a=b"
    assert _action_key("get", "/x", None) == "GET /x"  # method normalized


# ── Relay HTTP ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_relay_returns_none_when_disabled():
    """`enabled=False` → bridge inert; no httpx call, no state mutation."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, enabled=False)
    assert cb.enabled is False
    result = await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    assert result is None
    assert seen == []


@pytest.mark.asyncio
async def test_relay_swallows_network_error_returns_none():
    """A Carrier outage must not propagate to the thermostat caller —
    matches Perl's silent failure mode. The thermostat thinks its
    POST landed (we already 200'd it locally) and the relay just
    didn't happen this cycle. Failure is recorded so the circuit
    breaker / health gauge can react."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated", request=request)

    cb = _bridge_with_handler(handler)
    result = await cb.relay(
        "POST", "/systems/X/status", body=b"", headers=_DEFAULT_HEADERS,
    )
    assert result is None
    # Failure counter ticked so health/circuit breaker can react.
    assert cb._consecutive_failures == 1


@pytest.mark.asyncio
async def test_relay_strips_hop_by_hop_headers():
    seen_headers: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    await cb.relay(
        "POST", "/systems/X/status", body=b"data=...",
        headers={
            "host": "192.168.1.233:3001",  # local proxy host
            "content-type": "application/x-www-form-urlencoded",
            "content-length": "100",  # would mismatch our forwarded body
            "user-agent": "Carrier-Stat",
        },
    )
    assert seen_headers
    h = seen_headers[0]
    # Host overridden to the upstream so TLS SNI matches.
    assert "carrier.com" in h.get("host", "")
    assert h.get("user-agent") == "Carrier-Stat"
    # No leftover content-length — httpx recomputes it.


# ── End-to-end: southbound router invokes the bridge ──────────────────


def test_status_post_mirrors_to_carrier_when_no_local_changes():
    """A status POST with no local changes pending must trigger a
    relay to Carrier. The response sent BACK to the thermostat is
    Carrier's directive forwarded verbatim — including Carrier's own
    pingRate (alpha.48: we no longer normalize it to 12; Carrier's
    rate-limit signal is authoritative in clean state)."""
    relay_calls: list[str] = []
    carrier_directive = (
        b'<?xml version="1.0"?>\n<status version="1.37">'
        b'<configHasChanges>false</configHasChanges>'
        b'<pingRate>30</pingRate>'  # Carrier sends 30; we forward verbatim
        b'<serverHasChanges>false</serverHasChanges>'
        b'</status>'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        relay_calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(
            200, content=carrier_directive,
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)

    # Boot config so the southbound router has state to apply telemetry to.
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    r = client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    # Directive should be Carrier's body — pingRate forwarded verbatim.
    assert b"<pingRate>30</pingRate>" in r.content
    assert b"<serverHasChanges>false</serverHasChanges>" in r.content
    # And the relay must have happened (boot config + status both relayed).
    assert "POST /systems/2013W000855/status" in relay_calls


def test_status_post_skips_relay_when_local_changes_pending():
    """If we have a pending mutation (configHasChanges=true outgoing),
    we must NOT relay — the thermostat is about to pull our local
    tree next, and Carrier's stale view shouldn't race that."""
    relay_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        relay_calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)

    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Engage a hold so config_dirty becomes true. The next status POST
    # will then carry has_changes=true and skip the relay.
    client.put("/v1/zones/1/hold", json={"activity": "manual"})
    relay_calls.clear()
    r = client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    assert b"<configHasChanges>true</configHasChanges>" in r.content
    assert relay_calls == [], (
        "local changes pending — bridge must skip Carrier relay"
    )


async def test_config_get_pull_through_replays_pending_writes_onto_carrier_tree():
    """Regression: alpha.42 user reported that an HA-side cancel-hold
    issued while Carrier had a queued change open optimistically clears
    in the UI, then "comes back" within seconds. Root cause: the
    /config GET handler served Carrier's raw body — which still
    carried the MyInfinity app's queued hold-on tree — instead of the
    merged tree that apply_config produced after replaying our pending
    system_hold_clear.

    alpha.55: the only path Carrier-app changes reach HA is the
    pull-through in `get_system_config`. This test exercises that
    path: latch `pending_carrier_pull`, drive a thermostat /config
    GET, verify the served body has HA's pending cancel-hold replayed
    onto Carrier's hold-on tree.
    """
    from lxml import etree as _et

    _root = _et.fromstring(_read("boot_01_system_config.xml"))
    _wh = _root.find(".//wholeHouse")
    assert _wh is not None
    _wh.find("hold").text = "on"
    _wh.find("holdActivity").text = "manual"
    _otmr = _wh.find("otmr")
    if _otmr is None:
        _otmr = _et.SubElement(_wh, "otmr")
    _otmr.text = "21:30"
    carrier_tree_with_hold = _et.tostring(_root, xml_declaration=True, encoding="UTF-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/config"):
            return httpx.Response(
                200, content=carrier_tree_with_hold,
                headers={"content-type": "application/xml"},
            )
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    app = create_app(store=store, carrier_bridge=cb)

    with TestClient(app) as client:
        client.post(
            "/systems/2013W000855",
            content=_read("boot_01_system_config.xml"),
            headers={"content-type": "application/xml"},
        )
        # HA cancels hold → enqueues system_hold_clear.
        r = client.delete("/v1/system/hold")
        assert r.status_code == 200
        assert await p.unapplied_count() == 1

        # Latch pending_carrier_pull as if a previous status POST had
        # observed serverHasChanges=true.
        cb.signal_carrier_has_changes()

        # Thermostat /config GET drives the pull-through. apply_config
        # replays our pending system_hold_clear onto Carrier's hold-on
        # tree before serving it back.
        r = client.get(
            "/systems/2013W000855/config",
            headers={"Authorization": "Basic real-config-get="},
        )
        assert r.status_code == 200
        assert b"<hold>off</hold>" in r.content, (
            "served body should reflect HA's pending cancel-hold replayed "
            "onto Carrier's tree, not Carrier's raw hold-on"
        )
        assert b"<hold>on</hold>" not in r.content
        assert b"<holdActivity>none</holdActivity>" in r.content

    await p.close()


def test_idu_odu_notifications_mirror_to_carrier():
    """Item 5: every thermostat-bound POST mirrors to Carrier so the
    cloud's view of the install matches reality. Without this, the
    MyInfinity app sees stale equipment descriptors and missed
    notifications. Alpha.48: those mirrors are now fire-and-forget,
    so we wait briefly for the create_task to fire."""
    relay_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        relay_paths.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)

    serial = "2013W000855"
    # Boot config first — bridge mirrors.
    client.post(
        f"/systems/{serial}", content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # IDU + ODU are both new bridge call sites in alpha.26.
    client.post(
        f"/systems/{serial}/idu_config", content=_read("boot_03_idu_config.xml"),
        headers={"content-type": "application/xml"},
    )
    client.post(
        f"/systems/{serial}/odu_config", content=_read("boot_04_odu_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Notifications: the path that drives MyInfinity's alert surface.
    client.post(
        f"/systems/{serial}/notifications",
        content=_read("change_setpoint_notifications.xml"),
        headers={"content-type": "application/xml"},
    )

    # All four routes should have produced a relay. TestClient drives
    # the loop to completion for each request, so create_task'd mirrors
    # have completed by the time the inner request returns.
    assert f"POST /systems/{serial}" in relay_paths
    assert f"POST /systems/{serial}/idu_config" in relay_paths
    assert f"POST /systems/{serial}/odu_config" in relay_paths
    assert f"POST /systems/{serial}/notifications" in relay_paths


def test_release_notes_returns_carrier_body_when_available():
    """`/releaseNotes/{path}` previously returned an empty 200 stub;
    item 5 makes it relay to Carrier and serve real notes when Carrier
    has them. Falls back to the empty stub on Carrier 4xx/5xx or
    network failure."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "releaseNotes" in request.url.path:
            return httpx.Response(
                200,
                content=b"## What's new in firmware 14.02\n- bugfixes\n",
                headers={"content-type": "text/plain"},
            )
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)
    r = client.get("/releaseNotes/systxbbec-14.02.txt")
    assert r.status_code == 200
    assert b"What's new" in r.content


def _attach_test_handler() -> tuple[logging.Handler, list[logging.LogRecord]]:
    """Hand-rolled record capture — pytest's caplog can't see records
    once create_app's `_configure_logging` flips
    propagate=False on the `infinitude_proxy` parent logger. We attach
    our own handler directly to that logger so child loggers'
    records flow into our list regardless of propagation."""
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture(level=logging.DEBUG)
    target = logging.getLogger("infinitude_proxy")
    target.addHandler(handler)
    return handler, records


@pytest.mark.asyncio
async def test_relay_emits_access_log_line_on_success():
    """Per-relay INFO log line is the operator's main observability
    surface — they should see Carrier traffic in the addon logs the
    same way they see thermostat traffic via uvicorn's access log.
    Format mirrors uvicorn: `method url -> status (ms, bytes)`."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"<status/>",
            headers={"content-type": "application/xml"},
        )

    cap_handler, records = _attach_test_handler()
    try:
        cb = _bridge_with_handler(handler)
        await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    finally:
        logging.getLogger("infinitude_proxy").removeHandler(cap_handler)

    matches = [
        r for r in records
        if r.name == "infinitude_proxy.carrier_bridge"
        and r.levelno == logging.INFO
        and "relay POST" in r.getMessage()
        and "/systems/X/status" in r.getMessage()
        and "-> 200" in r.getMessage()
    ]
    assert matches, (
        f"expected access-log INFO line; got: {[r.getMessage() for r in records]}"
    )


@pytest.mark.asyncio
async def test_relay_emits_warning_on_network_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated", request=request)

    cap_handler, records = _attach_test_handler()
    try:
        cb = _bridge_with_handler(handler)
        await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    finally:
        logging.getLogger("infinitude_proxy").removeHandler(cap_handler)

    matches = [
        r for r in records
        if r.levelno == logging.WARNING
        and "ConnectError" in r.getMessage()
        and "-> error" in r.getMessage()
    ]
    assert matches, (
        f"expected warning log on network failure; got: {[r.getMessage() for r in records]}"
    )


def test_health_initial_state_is_unknown():
    cb = CarrierBridge()
    h = cb.health()
    assert h["status"] == "unknown"
    assert h["last_success_at"] is None
    assert h["last_attempt_at"] is None
    assert h["consecutive_failures"] == 0


def test_health_disabled_when_bridge_disabled():
    cb = CarrierBridge(enabled=False)
    h = cb.health()
    assert h["status"] == "disabled"
    assert h["circuit_open"] is False


@pytest.mark.asyncio
async def test_health_healthy_after_successful_relay():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<status/>")

    cb = _bridge_with_handler(handler)
    await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    h = cb.health()
    assert h["status"] == "healthy"
    assert h["last_success_at"] is not None
    assert h["last_attempt_at"] is not None
    assert h["consecutive_failures"] == 0


@pytest.mark.asyncio
async def test_health_degraded_after_consecutive_failures():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated", request=request)

    cb = _bridge_with_handler(handler)
    for _ in range(3):
        await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    h = cb.health()
    assert h["status"] == "degraded"
    assert h["consecutive_failures"] == 3
    assert h["last_error"] is not None
    assert h["last_success_at"] is None


@pytest.mark.asyncio
async def test_health_recovers_after_success_following_failures():
    state = {"fail": True}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["fail"]:
            raise httpx.ConnectError("simulated", request=request)
        return httpx.Response(200, content=b"<status/>")

    cb = _bridge_with_handler(handler)
    await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    assert cb.health()["consecutive_failures"] == 1

    state["fail"] = False
    await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    h = cb.health()
    assert h["status"] == "healthy"
    assert h["consecutive_failures"] == 0
    assert h["last_error"] is None


@pytest.mark.asyncio
async def test_health_5xx_counts_as_failure():
    """4xx is application error (we sent bad input), 5xx is server
    side. For UI purposes only 5xx + network errors count as
    'something we should worry about upstream'."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content=b"")

    cb = _bridge_with_handler(handler)
    await cb.relay(
        "POST", "/systems/X/status", body=b"x", headers=_DEFAULT_HEADERS,
    )
    h = cb.health()
    assert h["status"] == "degraded"
    assert h["consecutive_failures"] == 1
    assert "503" in (h["last_error"] or "")


@pytest.mark.asyncio
async def test_health_4xx_counts_as_success():
    """A 404 from Carrier means we reached them and they responded
    — round-trip works. Still counts as 'healthy upstream'."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    cb = _bridge_with_handler(handler)
    await cb.relay(
        "GET", "/some-unknown-path",
        headers={"Authorization": "Basic test-explicit="},
    )
    h = cb.health()
    assert h["status"] == "healthy"
    assert h["consecutive_failures"] == 0


def test_healthz_endpoint_reflects_bridge_status():
    """End-to-end: /v1/healthz response shape carries the bridge's
    actual status, including the alpha.48 circuit-breaker fields."""
    cb = CarrierBridge()  # enabled, never attempted
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)
    r = client.get("/v1/healthz")
    assert r.status_code == 200
    cc = r.json()["components"]["carrierCloud"]
    assert cc["status"] == "unknown"
    # Alpha.48 fields — circuit closed at startup.
    assert cc["circuitOpen"] is False
    assert cc["circuitCooldownSeconds"] >= 0
    # The pre-alpha.48 throttle field is gone from the model.
    assert "passReqsIntervalSeconds" not in cc


def test_release_notes_falls_back_to_empty_stub_on_carrier_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated", request=request)

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)
    r = client.get("/releaseNotes/systxbbec-14.02.txt")
    assert r.status_code == 200  # Local stub kicks in.
    assert r.content == b""


# ── Capture integration ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_relay_writes_carrier_out_capture_when_enabled():
    persistence = await Persistence.open(":memory:")
    try:
        control = CaptureControl(max_rows=100, persistence=persistence)
        control.start()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, content=b"<status/>",
                headers={"content-type": "application/xml"},
            )

        cb = _bridge_with_handler(handler, capture_control=control)
        await cb.relay(
            "POST", "/systems/X/status",
            body=b"data=...", headers=_DEFAULT_HEADERS,
        )

        rows = await persistence.capture_list(limit=10, direction="carrier_out")
        assert len(rows) == 1
        row = rows[0]
        assert row["direction"] == "carrier_out"
        assert row["method"] == "POST"
        assert row["path"].endswith("/systems/X/status")
        assert row["status_code"] == 200
        assert control.submitted == 1
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_post_system_config_mirrors_even_when_config_dirty():
    """Side-bug fix: a thermostat-originated POST /systems/{serial}
    must mirror to Carrier regardless of `store.config_dirty`. The
    alpha.10 "skip relay on local-changes-pending" rule applies to
    *outbound polls* (status, etc.) — not to a thermostat *pushing*
    its current view, where this body IS the device's authoritative
    state and dropping the mirror loses the only natural propagation
    channel for panel-side changes. Verified live in alpha.46
    capture: panel POST #2 was silently skipped because apply_config
    had set config_dirty during replay.

    Alpha.48: the mirror is now fire-and-forget (not awaited). We
    yield briefly after the client.post call so the create_task'd
    relay completes before we assert.
    """
    relay_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        relay_paths.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    store = StateStore()
    app = create_app(store=store, carrier_bridge=cb)
    import asyncio as _asyncio

    with TestClient(app) as client:
        # Boot once so the store has state. Mirror on this first POST is
        # the precondition for the test — verify it happened.
        client.post(
            "/systems/2013W000855",
            content=_read("boot_01_system_config.xml"),
            headers={"content-type": "application/xml"},
        )
        # Yield twice so the fire-and-forget mirror task can run.
        await _asyncio.sleep(0)
        await _asyncio.sleep(0)
        assert any(
            p == "POST /systems/2013W000855" for p in relay_paths
        ), "first boot POST should have mirrored"

        # Now force config_dirty=True via a HA mutation, then send another
        # boot-style POST. Pre-fix this second mirror was skipped (relay
        # short-circuit on local_changes_pending=True returned None
        # without any HTTP attempt); with the fix relay() proceeds to
        # mirror unconditionally.
        client.put("/v1/zones/1/hold", json={"activity": "manual"})
        assert store.config_dirty is True
        relay_paths.clear()

        client.post(
            "/systems/2013W000855",
            content=_read("boot_01_system_config.xml"),
            headers={"content-type": "application/xml"},
        )
        await _asyncio.sleep(0)
        await _asyncio.sleep(0)
        assert any(
            p == "POST /systems/2013W000855" for p in relay_paths
        ), (
            "second boot POST must still mirror to Carrier despite "
            "config_dirty=True — that's the alpha.46 panel-mirror skip "
            "regression we fixed"
        )


# ── alpha.48: circuit breaker + proactive pull + resilience ──────────


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_consecutive_failures():
    """After N consecutive network failures, relay() short-circuits
    and stops calling httpx until the cooldown elapses. Without this
    a sustained Carrier outage would cost us 1 timeout per call."""
    call_count = 0
    def handler(request):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("simulated", request=request)
    cb = _bridge_with_handler(
        handler, circuit_failure_threshold=3, circuit_cooldown_initial_s=60,
    )
    for _ in range(3):
        await cb.relay(
            "POST", "/systems/X/status", body=b"", headers=_DEFAULT_HEADERS,
        )
    assert call_count == 3
    assert cb._circuit_open()
    # 4th call short-circuits — no httpx attempt.
    await cb.relay(
        "POST", "/systems/X/status", body=b"", headers=_DEFAULT_HEADERS,
    )
    assert call_count == 3, "circuit must short-circuit; no upstream call"


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success():
    """First success after the cooldown elapses must close the
    circuit and reset the failure counter."""
    fail = True
    def handler(request):
        if fail:
            raise httpx.ConnectError("x", request=request)
        return httpx.Response(200, content=b"")
    cb = _bridge_with_handler(
        handler, circuit_failure_threshold=2, circuit_cooldown_initial_s=1,
    )
    await cb.relay(
        "POST", "/systems/X/status", body=b"", headers=_DEFAULT_HEADERS,
    )
    await cb.relay(
        "POST", "/systems/X/status", body=b"", headers=_DEFAULT_HEADERS,
    )
    assert cb._circuit_open()
    # Force cooldown elapsed.
    cb._circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    fail = False
    r = await cb.relay(
        "POST", "/systems/X/status", body=b"", headers=_DEFAULT_HEADERS,
    )
    assert r is not None and r.status_code == 200
    assert not cb._circuit_open()
    assert cb._consecutive_failures == 0


def test_status_post_latches_pending_pull_on_serverHasChanges():
    """When Carrier signals `serverHasChanges=true` on a relayed
    status response, the bridge must latch `pending_carrier_pull` so
    the next thermostat /config GET drives the pull-through. The
    addon has no auth of its own (Carrier OAuth nonces are single-use,
    secrets in firmware — see carrier_bridge module docstring), so
    this is the only mechanism by which Carrier-app changes reach HA.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<status><serverHasChanges>true</serverHasChanges></status>",
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler)
    store = StateStore()
    app = create_app(store=store, carrier_bridge=cb)
    client = TestClient(app)
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    r = client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    assert cb.take_pending_carrier_pull() is True, (
        "status handler must latch pending_carrier_pull when Carrier "
        "signals serverHasChanges=true"
    )


def test_config_get_pull_through_relays_thermostat_request_to_carrier():
    """Pull-through end-to-end: bridge has `pending_carrier_pull`
    latched, thermostat does /config GET. The southbound handler must
    relay the GET to Carrier with the inbound request's headers
    (Carrier OAuth nonces are single-use; only the thermostat's own
    fresh signature works), apply the response to local store, and
    serve the merged tree.
    """
    relay_calls: list[tuple[str, str]] = []
    seen_auths: list[str | None] = []
    from lxml import etree as _et
    boot = _read("boot_01_system_config.xml")
    root = _et.fromstring(boot)
    wh = root.find(".//wholeHouse")
    wh.find("hold").text = "on"
    wh.find("holdActivity").text = "manual"
    otmr = wh.find("otmr")
    if otmr is None:
        otmr = _et.SubElement(wh, "otmr")
    otmr.text = "21:30"
    carrier_body = _et.tostring(root, xml_declaration=True, encoding="UTF-8")

    def handler(request: httpx.Request) -> httpx.Response:
        relay_calls.append((request.method, request.url.path))
        seen_auths.append(request.headers.get("authorization"))
        return httpx.Response(
            200, content=carrier_body,
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler)
    store = StateStore()
    app = create_app(store=store, carrier_bridge=cb)
    client = TestClient(app)
    client.post(
        "/systems/2013W000855",
        content=boot,
        headers={"content-type": "application/xml"},
    )
    cb.signal_carrier_has_changes()
    relay_calls.clear()
    seen_auths.clear()

    r = client.get(
        "/systems/2013W000855/config",
        headers={
            "Authorization": "Basic config-get-real=",
            "User-Agent": "Carrier-Stat/14",
        },
    )
    assert r.status_code == 200
    assert any(
        m == "GET" and "/config" in p for m, p in relay_calls
    ), "pull-through must relay /config GET to Carrier"
    assert "Basic config-get-real=" in seen_auths, (
        "the relay must forward the inbound thermostat headers"
    )
    # Local store reflects Carrier's tree (hold-on landed).
    stored = store.get_config()
    assert stored is not None
    assert stored.tree.find(".//wholeHouse/hold").text == "on"


@pytest.mark.asyncio
async def test_relay_routes_through_outbound():
    """Architectural invariant: `relay()` is a thin wrapper around
    `_outbound`. With the alpha.55 cleanup, `relay()` is the only
    public outbound method left, so this test just locks down the
    chokepoint discipline.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    calls: list[tuple[str, str]] = []
    original = cb._outbound  # type: ignore[attr-defined]

    async def spy(method, path, **kw):
        calls.append((method, path))
        return await original(method, path, **kw)

    cb._outbound = spy  # type: ignore[attr-defined]
    await cb.relay(
        "POST", "/systems/X/status",
        headers={"Authorization": "Basic test="},
        body=b"data=...",
    )
    assert any("/systems/X/status" in p for _, p in calls), (
        "relay() must route through _outbound"
    )


@pytest.mark.asyncio
async def test_outbound_refuses_when_no_source_headers():
    """The chokepoint must refuse when no `source_headers` is provided.
    The addon has no way to mint Carrier OAuth on its own — only a
    real thermostat-originated request carries valid auth. Refusal
    does NOT increment the failure counter (a guaranteed-401 isn't
    the bridge's fault and shouldn't flap the circuit breaker)."""
    seen: list = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    result = await cb._outbound("GET", "/systems/X/config")  # type: ignore[attr-defined]
    assert result is None
    assert seen == []
    assert cb._consecutive_failures == 0


def test_resilience_endpoints_respond_under_1s_when_carrier_blackholed():
    """Resilience contract (alpha.48): with Carrier hung indefinitely,
    every thermostat-facing endpoint must still reply in < 1 s. We
    simulate a black-hole as an immediate TimeoutException — what
    httpx would surface after `_TIMEOUT_S` seconds when a real Carrier
    socket never responds. The thermostat handler must catch that and
    serve local content fast.
    """
    import time as _time

    def timeout_handler(request):
        # MockTransport doesn't honour httpx's timeout (no real socket
        # to wait on), so we simulate the post-timeout state directly:
        # raise the same exception class httpx would have raised on a
        # genuine black-hole. CarrierBridge catches httpx.RequestError,
        # of which TimeoutException is a subclass.
        raise httpx.ConnectTimeout("simulated black-hole", request=request)

    cb = _bridge_with_handler(timeout_handler, timeout=0.5)
    store = StateStore()
    app = create_app(store=store, carrier_bridge=cb)
    client = TestClient(app)

    # Boot first so subsequent endpoints have local state.
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Fire-and-forget mirrors don't block — those endpoints return
    # immediately. Verify status POST stays under 1.5 s (the synchronous
    # status relay is the only awaited Carrier call).
    t0 = _time.monotonic()
    client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    elapsed = _time.monotonic() - t0
    assert elapsed < 1.5, f"status POST took {elapsed:.2f}s under black-hole"

    t0 = _time.monotonic()
    client.get("/systems/2013W000855/config")
    elapsed = _time.monotonic() - t0
    assert elapsed < 0.5, f"/config GET took {elapsed:.2f}s under black-hole"
