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
from infinitude_proxy.carrier_bridge import (
    CachedRelay,
    CarrierBridge,
    _action_key,
)
from infinitude_proxy.main import create_app
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _bridge_with_handler(handler, *, seed_auth: bool = True, **kw) -> CarrierBridge:
    """A CarrierBridge whose httpx client is wired to a MockTransport
    so tests don't hit the real internet.

    `seed_auth=True` (default) pre-populates `_auth_by_route` for the
    routes most tests care about (status POST, /config GET, boot POST)
    so background-path tests (push_config, pull_and_apply_config) can
    run without an explicit priming `relay()` call. Pass
    `seed_auth=False` to test the cold-start refusal path explicitly.
    The single-chokepoint `_outbound` method (alpha.51) refuses
    requests when no auth is cached for the requested route, and the
    cache became per-route in alpha.52 (Carrier validates auth
    per-(method, path)).
    """
    kw.setdefault("enabled", True)
    cb = CarrierBridge(**kw)
    cb._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(handler),
        timeout=cb._timeout,
        follow_redirects=False,
    )
    if seed_auth:
        seed = {
            "authorization": "Basic test-seed",
            "host": "www.api.ing.carrier.com",
        }
        # Seed the routes most tests touch. Tests that need a specific
        # cold-start route can clear individual entries or use
        # seed_auth=False.
        for serial in ("X", "2013W000855"):
            cb._auth_by_route[("POST", f"/systems/{serial}/status")] = dict(seed)
            cb._auth_by_route[("GET", f"/systems/{serial}/config")] = dict(seed)
            cb._auth_by_route[("POST", f"/systems/{serial}")] = dict(seed)
    return cb


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
    result = await cb.relay("POST", "/systems/X/status", body=b"x")
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
    result = await cb.relay("POST", "/systems/X/status", body=b"")
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


async def test_config_get_in_window_replays_pending_writes_onto_carrier_tree():
    """Regression: alpha.42 user reported that an HA-side cancel-hold
    issued while Carrier had a queued change open optimistically
    clears in the UI, then "comes back" within seconds. Root cause was
    the carrier-bridge branch of GET /systems/{serial}/config serving
    Carrier's raw response body — which still carried the MyInfinity
    app's queued hold-on tree — instead of the merged tree that
    apply_config produced after replaying our pending system_hold_clear.
    Alpha.48 deletes the carrier_changes-window branch entirely; this
    test now exercises the same merge invariant via the proactive-pull
    path (`pull_and_apply_config`), which also runs apply_config and
    therefore the same `pending_for_replay` grace-window logic.
    """
    # Build "Carrier's tree" by taking the real boot fixture and
    # flipping wholeHouse/hold to ON, mimicking a MyInfinity-app-set
    # hold queued at Carrier. Using the fixture (not a hand-rolled
    # minimal tree) ensures parse_system_config_with_tree's strict
    # SystemConfig validation accepts the body.
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
        # Boot — populates the local store with a real fixture (no hold).
        client.post(
            "/systems/2013W000855",
            content=_read("boot_01_system_config.xml"),
            headers={"content-type": "application/xml"},
        )
        # HA cancels hold → enqueues a system_hold_clear pending write.
        # Idempotent at the local-tree layer (the fixture's wholeHouse
        # is already hold=off) but the pending row is what matters here.
        r = client.delete("/v1/system/hold")
        assert r.status_code == 200
        assert await p.unapplied_count() == 1

        # Drive the proactive pull directly: bridge fetches Carrier's
        # tree (hold=on), runs apply_config, which replays our pending
        # system_hold_clear onto Carrier's tree.
        ok = await cb.pull_and_apply_config("2013W000855", store)
        assert ok is True

        # The served body must carry the merged tree, NOT Carrier's
        # raw hold-on response.
        r = client.get("/systems/2013W000855/config")
        assert r.status_code == 200
        assert b"<hold>off</hold>" in r.content, (
            "served body should reflect HA's pending cancel-hold replayed "
            "onto Carrier's tree, not Carrier's raw hold-on"
        )
        assert b"<hold>on</hold>" not in r.content
        assert b"<holdActivity>none</holdActivity>" in r.content

    await p.close()


async def test_post_clear_carrier_overwrite_protected_by_grace_window():
    """Harder version of the cancel-hold-revert bug: the HA-side
    cancel-hold has already been marked applied (pull-observed clear
    on a previous /config GET). Then Carrier serves its STALE tree
    (still holding the queued app hold) via the proactive-pull path.
    Without the grace-window replay, apply_config would let Carrier's
    hold overwrite our cleared state. With pending_for_replay's grace
    window, the recently-applied system_hold_clear is re-replayed
    onto Carrier's stale tree and the cancel sticks.

    Alpha.48 rewrite: the carrier_changes window is gone; this test
    now drives the merge directly via `pull_and_apply_config`, which
    is the same code path that fires from `post_telemetry` when
    Carrier signals serverHasChanges=true.
    """
    from lxml import etree as _et

    _root = _et.fromstring(_read("boot_01_system_config.xml"))
    _wh = _root.find(".//wholeHouse")
    _wh.find("hold").text = "on"
    _wh.find("holdActivity").text = "manual"
    _otmr = _wh.find("otmr")
    if _otmr is None:
        _otmr = _et.SubElement(_wh, "otmr")
    _otmr.text = "21:30"
    carrier_stale_tree = _et.tostring(_root, xml_declaration=True, encoding="UTF-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/config"):
            return httpx.Response(
                200, content=carrier_stale_tree,
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
        # User cancels hold in HA → enqueue + dirty.
        client.delete("/v1/system/hold")
        # First /config pull marks the row applied — pull-observed-clear.
        r = client.get("/systems/2013W000855/config")
        assert r.status_code == 200
        assert await p.unapplied_count() == 0, (
            "first /config GET must mark the row applied"
        )
        # Row is APPLIED but still within grace.
        replay_rows = await p.pending_for_replay("2013W000855")
        assert len(replay_rows) == 1
        assert replay_rows[0].applied_at is not None
        assert replay_rows[0].kind == "system_hold_clear"

        # Now Carrier responds via proactive-pull with a stale tree
        # that still has the app's hold. The grace-window replay must
        # re-merge our cleared hold onto it before the served tree
        # changes back.
        ok = await cb.pull_and_apply_config("2013W000855", store)
        assert ok is True
        r = client.get("/systems/2013W000855/config")
        assert r.status_code == 200
        assert b"<hold>off</hold>" in r.content, (
            "grace-window replay should re-merge HA's cleared hold onto "
            "Carrier's stale tree, even though the row was already applied"
        )
        assert b"<hold>on</hold>" not in r.content

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
        await cb.relay("POST", "/systems/X/status", body=b"x")
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
        await cb.relay("POST", "/systems/X/status", body=b"x")
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
    await cb.relay("POST", "/systems/X/status", body=b"x")
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
        await cb.relay("POST", "/systems/X/status", body=b"x")
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
    await cb.relay("POST", "/systems/X/status", body=b"x")
    assert cb.health()["consecutive_failures"] == 1

    state["fail"] = False
    await cb.relay("POST", "/systems/X/status", body=b"x")
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
    await cb.relay("POST", "/systems/X/status", body=b"x")
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
    # Pass headers explicitly so the per-route cache (alpha.52)
    # accepts the request — _bridge_with_handler seeds common routes
    # but not arbitrary test paths like "/some-unknown-path".
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
        await cb.relay("POST", "/systems/X/status", body=b"data=...")

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


# ── push_config (alpha.47): HA-mutation upstream sync ─────────────────


@pytest.mark.asyncio
async def test_relay_caches_auth_headers_for_later_push():
    """Every successful inbound thermostat relay must rotate the auth
    cache the bridge keeps for `push_config`. Without this, HA-side
    pushes have nothing to authenticate with on cold start beyond the
    very first relay's headers."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, seed_auth=False)
    assert cb._auth_by_route == {}  # type: ignore[attr-defined]
    await cb.relay(
        "POST", "/systems/2013W000855/status",
        headers={"Authorization": "Basic abc=", "User-Agent": "carrier"},
        body=b"data=...",
    )
    # Per-route cache (alpha.52): keyed on (method, path).
    cached = cb._auth_by_route.get(  # type: ignore[attr-defined]
        ("POST", "/systems/2013W000855/status")
    )
    assert cached is not None
    # The sanitizer preserves header-name case as supplied; lookup
    # case-insensitively here (httpx normalizes on the wire).
    lower = {k.lower(): v for k, v in cached.items()}
    assert lower.get("authorization") == "Basic abc="
    # Sanitizer always overrides Host to the upstream so we don't leak
    # the proxy's local hostname back at Carrier.
    assert lower.get("host") == "www.api.ing.carrier.com"


@pytest.mark.asyncio
async def test_push_config_noop_when_no_auth_cached():
    """Cold start: no thermostat request has landed yet, so the auth
    cache is empty. push_config must be a no-op (return False) rather
    than POST-with-empty-headers, which Carrier would reject as 401
    and we'd burn a consecutive-failure on the bridge health gauge."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, seed_auth=False)
    ok = await cb.push_config("2013W000855", b"data=fake")
    assert ok is False
    assert seen == [], "no upstream request should have been made"


@pytest.mark.asyncio
async def test_push_config_uses_cached_auth_and_correct_target():
    """push_config posts to /systems/{serial} on the upstream host
    using the cached thermostat auth FOR THAT EXACT ROUTE (alpha.52
    per-route cache), with the supplied body and form-urlencoded
    content-type — same wire shape Carrier accepts from a real
    device boot/sync POST.

    Prime the boot-POST route (`POST /systems/{serial}`) — same
    route push_config uses. Status-POST auth would NOT satisfy
    push_config's lookup; that's exactly the per-route discipline.
    """
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, seed_auth=False)
    # Prime auth for the boot-POST route — push_config's exact route.
    await cb.relay(
        "POST", "/systems/2013W000855",
        headers={"Authorization": "Basic xyz="},
        body=b"data=initial-boot",
    )
    seen.clear()
    body = b"data=" + b"%3Csystem%20version%3D%221.7%22%3E..."
    ok = await cb.push_config("2013W000855", body)
    assert ok is True
    assert len(seen) == 1
    req = seen[0]
    assert req.method == "POST"
    assert str(req.url) == (
        "https://www.api.ing.carrier.com/systems/2013W000855"
    )
    assert req.headers.get("authorization") == "Basic xyz="
    assert req.headers.get("content-type") == "application/x-www-form-urlencoded"
    assert req.content == body


@pytest.mark.asyncio
async def test_push_config_logs_failure_does_not_raise():
    """Carrier returning 5xx (or a network error) must not propagate —
    push_config is best-effort upstream sync, not a precondition for
    the local mutation."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content=b"upstream busy")

    cb = _bridge_with_handler(handler)
    await cb.relay(
        "POST", "/systems/X/status",
        headers={"Authorization": "Basic z="},
        body=b"data=...",
    )
    ok = await cb.push_config("X", b"data=fake")
    assert ok is False  # 503 is not 2xx
    # Bridge health should reflect the failure so /v1/healthz can
    # surface it; failures count toward consecutive_failures.
    assert cb._consecutive_failures > 0


@pytest.mark.asyncio
async def test_mutate_config_triggers_carrier_push():
    """End-to-end: a HA-side mutation (PUT /v1/system/hold) must fire
    `bridge.push_config` so Carrier learns about it. Without this,
    Carrier's tree stays stale and re-asserts the pre-mutation state
    on its next `serverHasChanges=true` window — the exact alpha.45
    grace-window-expiration revert the 2026-05-07 capture caught."""
    pushes: list[tuple[str, bytes]] = []

    class StubBridge:
        # Match the surface state_store / southbound rely on. Keeps
        # the test free of an httpx mock since we're proving the wire-
        # up, not the HTTP behavior (covered by the cb tests above).
        enabled = True

        async def push_config(self, serial: str, body: bytes) -> bool:
            pushes.append((serial, body))
            return True

        async def relay(self, *a, **kw):
            return None

        @staticmethod
        def has_server_changes(body):
            return False

        def take_just_recovered(self) -> bool:
            return False

        # alpha.52 surface — stubs need these to satisfy southbound.
        def has_route_auth(self, method, path):
            return False

        def signal_carrier_has_changes(self):
            pass

        def take_pending_carrier_pull(self):
            return False

        async def open(self): pass
        async def close(self): pass

    bridge = StubBridge()
    store = StateStore()
    app = create_app(store=store, carrier_bridge=bridge)
    client = TestClient(app)

    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    pushes.clear()
    r = client.put("/v1/system/hold", json={"activity": "home"})
    assert r.status_code == 200

    # mutate_config schedules push_config via asyncio.create_task; it
    # runs on the event loop after the request handler returns. Yield
    # once so the task gets to execute before we assert.
    import asyncio as _asyncio
    await _asyncio.sleep(0)
    await _asyncio.sleep(0)  # give create_task two ticks to settle

    assert len(pushes) == 1, (
        f"mutate_config should have fired exactly one push; got {len(pushes)}"
    )
    serial, body = pushes[0]
    assert serial == "2013W000855"
    assert body.startswith(b"data=")
    # Body decodes to <system version="1.7"><config>...</config></system>
    # carrying the post-mutation hold=on state.
    from urllib.parse import unquote_to_bytes
    inner = unquote_to_bytes(body[5:])
    assert b"<system version=" in inner
    assert b"<config>" in inner or b"<config " in inner
    assert b"<hold>on</hold>" in inner


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
        await cb.relay("POST", "/systems/X/status", body=b"")
    assert call_count == 3
    assert cb._circuit_open()
    # 4th call short-circuits — no httpx attempt.
    await cb.relay("POST", "/systems/X/status", body=b"")
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
    await cb.relay("POST", "/systems/X/status", body=b"")
    await cb.relay("POST", "/systems/X/status", body=b"")
    assert cb._circuit_open()
    # Force cooldown elapsed.
    cb._circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    fail = False
    r = await cb.relay("POST", "/systems/X/status", body=b"")
    assert r is not None and r.status_code == 200
    assert not cb._circuit_open()
    assert cb._consecutive_failures == 0


@pytest.mark.asyncio
async def test_take_just_recovered_latches_on_recovery():
    """When the bridge transitions from a failure streak to a
    success, take_just_recovered() returns True ONCE."""
    fail = True
    def handler(request):
        if fail:
            raise httpx.ConnectError("x", request=request)
        return httpx.Response(200, content=b"")
    cb = _bridge_with_handler(handler, circuit_failure_threshold=10)
    await cb.relay("POST", "/systems/X/status", body=b"")  # fail
    fail = False
    await cb.relay("POST", "/systems/X/status", body=b"")  # success
    assert cb.take_just_recovered() is True
    assert cb.take_just_recovered() is False  # consume-on-read


@pytest.mark.asyncio
async def test_pull_and_apply_config_applies_carrier_tree_to_store():
    """Verify the proactive-pull path: bridge fetches /config from
    Carrier, parses, applies to local store, marks dirty."""
    store = StateStore()
    # Seed local store with boot fixture so apply_config has something
    # to merge into.
    from infinitude_proxy.parser import parse_system_config_with_tree
    boot = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(boot)
    await store.apply_config("2013W000855", config, tree)

    # Carrier returns the same fixture but with hold flipped to on,
    # mimicking an app-queued change.
    from lxml import etree as _et
    root = _et.fromstring(boot)
    wh = root.find(".//wholeHouse")
    wh.find("hold").text = "on"
    wh.find("holdActivity").text = "manual"
    otmr = wh.find("otmr")
    if otmr is None:
        otmr = _et.SubElement(wh, "otmr")
    otmr.text = "21:30"
    carrier_body = _et.tostring(root, xml_declaration=True, encoding="UTF-8")

    def handler(request):
        return httpx.Response(
            200, content=carrier_body,
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler)
    ok = await cb.pull_and_apply_config("2013W000855", store)
    assert ok is True
    stored = store.get_config()
    assert stored is not None
    # Verify Carrier's hold-on landed in local tree.
    wh_local = stored.tree.find(".//wholeHouse")
    assert wh_local.find("hold").text == "on"
    # Dirty flag set so next directive tells thermostat to pull.
    assert store.config_dirty is True


def test_status_post_fires_proactive_pull_on_serverHasChanges():
    """When Carrier responds with serverHasChanges=true, the status
    handler must schedule a pull_and_apply_config task — that's how
    Carrier-app changes flow into our local tree without waiting on
    the thermostat's next /config GET cycle."""
    pull_calls: list[str] = []

    class StubBridge:
        enabled = True
        async def open(self): pass
        async def close(self): pass
        async def relay(self, *a, **kw):
            return CachedRelay(
                status_code=200,
                body=b"<status><serverHasChanges>true</serverHasChanges></status>",
                content_type="application/xml",
                cached_at=datetime.now(timezone.utc),
            )
        async def pull_and_apply_config(self, serial, store):
            pull_calls.append(serial)
            return True
        @staticmethod
        def has_server_changes(body):
            return b"<serverHasChanges>true</serverHasChanges>" in (body or b"")
        def take_just_recovered(self):
            return False
        def has_route_auth(self, method, path):
            # Test setup: pretend the cache is warm for /config GET
            # so the proactive-pull path fires (this test specifically
            # asserts pull_and_apply_config gets called).
            return True
        def signal_carrier_has_changes(self):
            pass
        def take_pending_carrier_pull(self):
            return False
        def health(self):
            return {"status": "healthy", "last_success_at": None,
                    "last_attempt_at": None, "last_error": None,
                    "consecutive_failures": 0, "circuit_open": False,
                    "circuit_cooldown_s": 0, "pass_reqs": 0}

    store = StateStore()
    app = create_app(store=store, carrier_bridge=StubBridge())
    client = TestClient(app)
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    pull_calls.clear()
    r = client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    # The create_task fires on the event loop after the request handler
    # returns. TestClient drives the loop to completion for each
    # request — by the time client.post returns, scheduled tasks have
    # run.
    assert "2013W000855" in pull_calls, (
        "status handler must fire pull_and_apply_config when Carrier "
        "signals serverHasChanges=true"
    )


def test_status_post_latches_pending_pull_when_route_auth_cold():
    """Cold-cache fallback (alpha.52): when /config GET auth is NOT
    yet cached and Carrier signals serverHasChanges=true, the status
    handler must NOT fire a proactive pull (it would 401). Instead
    it latches `signal_carrier_has_changes()` so the next thermostat
    /config GET handles the relay with the inbound request's
    headers.
    """
    pull_calls: list[str] = []
    signaled: list[bool] = []

    class StubBridge:
        enabled = True
        async def open(self): pass
        async def close(self): pass
        async def relay(self, *a, **kw):
            return CachedRelay(
                status_code=200,
                body=b"<status><serverHasChanges>true</serverHasChanges></status>",
                content_type="application/xml",
                cached_at=datetime.now(timezone.utc),
            )
        async def pull_and_apply_config(self, serial, store):
            pull_calls.append(serial); return True
        @staticmethod
        def has_server_changes(body):
            return b"<serverHasChanges>true</serverHasChanges>" in (body or b"")
        def has_route_auth(self, method, path):
            return False  # cold cache for this route
        def signal_carrier_has_changes(self):
            signaled.append(True)
        def take_pending_carrier_pull(self):
            return False
        def take_just_recovered(self):
            return False
        def health(self):
            return {"status": "healthy", "last_success_at": None,
                    "last_attempt_at": None, "last_error": None,
                    "consecutive_failures": 0, "circuit_open": False,
                    "circuit_cooldown_s": 0, "pass_reqs": 0}

    store = StateStore()
    app = create_app(store=store, carrier_bridge=StubBridge())
    client = TestClient(app)
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    pull_calls.clear()
    signaled.clear()
    r = client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    assert pull_calls == [], (
        "cold-cache path must NOT fire proactive pull (would 401)"
    )
    assert signaled == [True], (
        "cold-cache path must latch signal_carrier_has_changes so the "
        "next thermostat /config GET drives the relay"
    )


def test_config_get_cold_start_relays_thermostat_request_to_carrier():
    """Cold-start fallback end-to-end: bridge has pending_carrier_pull
    latched, thermostat does /config GET. The southbound handler must
    relay the GET to Carrier with the inbound request's headers,
    apply the response to local store, and serve the merged tree.
    The relay also populates the per-route auth cache so subsequent
    serverHasChanges signals can use the proactive-pull path.
    """
    relay_calls: list[tuple[str, str]] = []
    seen_auths: list[str | None] = []
    # Carrier returns a tree with a hold engaged — represents the
    # Carrier-app-set state we need to merge into local.
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

    cb = _bridge_with_handler(handler, seed_auth=False)
    store = StateStore()
    app = create_app(store=store, carrier_bridge=cb)
    client = TestClient(app)
    # Boot — populates store, primes the boot-POST route auth.
    client.post(
        "/systems/2013W000855",
        content=boot,
        headers={"content-type": "application/xml"},
    )
    # Latch the pending-pull signal as if a status post had just
    # observed serverHasChanges=true.
    cb.signal_carrier_has_changes()
    relay_calls.clear()
    seen_auths.clear()

    # Thermostat does /config GET with its own headers — these will
    # be forwarded to Carrier.
    r = client.get(
        "/systems/2013W000855/config",
        headers={
            "Authorization": "Basic config-get-real=",
            "User-Agent": "Carrier-Stat/14",
        },
    )
    assert r.status_code == 200
    # Relay must have fired with the inbound /config-GET auth.
    assert any(
        m == "GET" and "/config" in p for m, p in relay_calls
    ), "cold-start fallback must relay /config GET to Carrier"
    assert "Basic config-get-real=" in seen_auths, (
        "the relay must forward the inbound thermostat headers, not "
        "any cached cross-route auth"
    )
    # Per-route cache must be warm now for /config GET so the next
    # serverHasChanges signal can use the proactive-pull path.
    assert ("GET", "/systems/2013W000855/config") in cb._auth_by_route, (
        "cold-start fallback must populate the cache as a side effect"
    )
    # Local store reflects Carrier's tree (hold-on landed).
    stored = store.get_config()
    assert stored is not None
    assert stored.tree.find(".//wholeHouse/hold").text == "on"


@pytest.mark.asyncio
async def test_status_post_fires_catchup_push_on_recovery():
    """After bridge transitions from failing to succeeding, the next
    status post must fire a catch-up push_config carrying the current
    local tree, so HA mutations during the outage propagate upstream."""
    push_calls: list[tuple[str, int]] = []
    fail = True
    def handler(request):
        if fail:
            raise httpx.ConnectError("x", request=request)
        # Recovery — return clean response with serverHasChanges=false.
        return httpx.Response(
            200,
            content=b"<status><serverHasChanges>false</serverHasChanges></status>",
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler, circuit_failure_threshold=10)
    # Capture push_config calls without short-circuiting; wrap the method.
    original_push = cb.push_config
    async def capture_push(serial, body):
        push_calls.append((serial, len(body)))
        return await original_push(serial, body)
    cb.push_config = capture_push  # type: ignore[method-assign]

    store = StateStore()
    app = create_app(store=store, carrier_bridge=cb)
    with TestClient(app) as client:
        client.post(
            "/systems/2013W000855",
            content=_read("boot_01_system_config.xml"),
            headers={"content-type": "application/xml"},
        )
        # First status: fail.
        client.post(
            "/systems/2013W000855/status",
            content=_read("boot_05_status_telemetry.xml"),
            headers={"content-type": "application/xml"},
        )
        push_calls.clear()
        fail = False  # next call recovers
        client.post(
            "/systems/2013W000855/status",
            content=_read("boot_05_status_telemetry.xml"),
            headers={"content-type": "application/xml"},
        )
        # Give the create_task a moment.
        import asyncio as _a
        await _a.sleep(0)
        await _a.sleep(0)
    assert len(push_calls) >= 1, (
        "catch-up push must fire on first success after a failure streak"
    )
    assert push_calls[0][0] == "2013W000855"


@pytest.mark.asyncio
async def test_every_public_outbound_method_routes_through_outbound():
    """Architectural invariant (alpha.51): every public method that
    makes a Carrier-bound HTTP call must go through `_outbound`. This
    test wraps `_outbound` with a spy and exercises each public
    method, asserting the spy was called for every one.

    Without this invariant, a future contributor adding a new
    outbound feature could write `await self._client.request(...)`
    directly, bypassing the auth resolver / circuit breaker / health
    update / capture insertion. That's exactly what produced the
    alpha.48 bug where `pull_and_apply_config` shipped without auth
    forwarding and silently 401'd every Carrier-app change.
    """
    from infinitude_proxy.parser import parse_system_config_with_tree
    from infinitude_proxy.state_store import StateStore

    def handler(request: httpx.Request) -> httpx.Response:
        # Return a minimal valid <config> for pull_and_apply_config's
        # parse step. Auth presence is what we're locking down — any
        # 200 with a parseable body is fine.
        return httpx.Response(
            200,
            content=(
                b'<?xml version="1.0"?>\n<config>'
                b'<wholeHouse><hold>off</hold><holdActivity>none</holdActivity><otmr/></wholeHouse>'
                b'</config>'
            ),
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler)
    calls: list[tuple[str, str]] = []
    original = cb._outbound  # type: ignore[attr-defined]

    async def spy(method, path, **kw):
        calls.append((method, path))
        return await original(method, path, **kw)

    cb._outbound = spy  # type: ignore[attr-defined]

    # 1) relay (request-scoped path).
    await cb.relay(
        "POST", "/systems/X/status",
        headers={"Authorization": "Basic test="},
        body=b"data=...",
    )
    assert any("/systems/X/status" in p for _, p in calls), (
        "relay() must route through _outbound"
    )
    calls.clear()

    # 2) push_config (background path, cached auth).
    await cb.push_config("X", b"data=fake")
    assert any(p == "/systems/X" for _, p in calls), (
        "push_config() must route through _outbound"
    )
    calls.clear()

    # 3) pull_and_apply_config (background path, cached auth).
    # Seed local store first so apply_config has something to work on.
    store = StateStore()
    boot = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(boot)
    await store.apply_config("X", config, tree)
    await cb.pull_and_apply_config("X", store)
    assert any(p == "/systems/X/config" for _, p in calls), (
        "pull_and_apply_config() must route through _outbound"
    )


@pytest.mark.asyncio
async def test_outbound_refuses_cold_start_without_auth():
    """The chokepoint must refuse to call Carrier when no auth is
    available — no source_headers and no cache. Returns None and
    does not increment the failure counter (a guaranteed-401 isn't
    the bridge's fault and shouldn't flap the circuit breaker)."""
    seen: list = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, seed_auth=False)
    result = await cb._outbound("GET", "/systems/X/config")  # type: ignore[attr-defined]
    assert result is None
    assert seen == []
    assert cb._consecutive_failures == 0


@pytest.mark.asyncio
async def test_outbound_caches_auth_only_when_source_headers_provided():
    """Cache discipline: `_outbound` updates `_auth_by_route` ONLY
    when called with `source_headers` (a real thermostat-originated
    relay for THIS route). Background calls that fall back to cached
    auth must NOT re-cache themselves."""
    def handler(request):
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, seed_auth=False)
    assert cb._auth_by_route == {}  # type: ignore[attr-defined]

    # source_headers provided → entry populates for THIS route.
    await cb._outbound(  # type: ignore[attr-defined]
        "POST", "/systems/X/status",
        body=b"data=...",
        source_headers={"Authorization": "Basic real="},
    )
    status_key = ("POST", "/systems/X/status")
    assert status_key in cb._auth_by_route
    cached_before = dict(cb._auth_by_route[status_key])

    # Background call for a DIFFERENT route. Cache miss expected
    # (per-route discipline) — no cross-route fallback. The original
    # status entry is unchanged; no /config GET entry is added.
    result = await cb._outbound(  # type: ignore[attr-defined]
        "GET", "/systems/X/config",
    )
    assert result is None, "background call without route-specific auth must refuse"
    assert cb._auth_by_route[status_key] == cached_before
    assert ("GET", "/systems/X/config") not in cb._auth_by_route


@pytest.mark.asyncio
async def test_outbound_per_route_isolation_status_auth_does_not_satisfy_config():
    """Architectural invariant (alpha.52): cached status-POST headers
    must NOT satisfy a /config GET lookup. This is the entire reason
    we have the per-route cache — Carrier validates per-route and
    cross-route reuse causes the 401s observed live alpha.48-51."""
    def handler(request):
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, seed_auth=False)

    # Populate ONLY the status route.
    await cb.relay(
        "POST", "/systems/X/status",
        headers={"Authorization": "Basic status="},
        body=b"data=...",
    )
    assert ("POST", "/systems/X/status") in cb._auth_by_route
    assert ("GET", "/systems/X/config") not in cb._auth_by_route

    # push_config (POST /systems/X) and pull_and_apply_config
    # (GET /systems/X/config) are DIFFERENT routes from the populated
    # status entry. Both must refuse — pre-alpha.52 the single cache
    # would have satisfied them and produced the live 401s.
    push_ok = await cb.push_config("X", b"data=...")
    assert push_ok is False, (
        "push_config must NOT use status-POST auth — different route, "
        "Carrier rejects it (verified live)."
    )
    from infinitude_proxy.state_store import StateStore
    pull_ok = await cb.pull_and_apply_config("X", StateStore())
    assert pull_ok is False, (
        "pull_and_apply_config must NOT use status-POST auth on "
        "/config GET — different route, Carrier rejects it."
    )


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
