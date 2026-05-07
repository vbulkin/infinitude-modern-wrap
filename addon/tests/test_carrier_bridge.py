"""CarrierBridge — implicit thermostat → Carrier-cloud relay.

Companion to test_forward_proxy.py. Where the forward proxy handles
explicit `/http%3A//host/...` URL-encoded paths, the bridge handles
the *implicit* relay the legacy Perl Infinitude does in
`before_dispatch`: mirror status POSTs upstream, track Carrier's
`serverHasChanges` flag, gate config GETs on the carrier-changes
window so MyInfinity-app round-trips work.
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
    CarrierBridge,
    _action_key,
)
from infinitude_proxy.main import create_app
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _bridge_with_handler(handler, **kw) -> CarrierBridge:
    """A CarrierBridge whose httpx client is wired to a MockTransport
    so tests don't hit the real internet."""
    cb = CarrierBridge(**kw)
    cb._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(handler),
        timeout=cb._timeout,
        follow_redirects=False,
    )
    return cb


# ── Pure decision logic ───────────────────────────────────────────────


def test_should_relay_disabled_when_pass_reqs_is_zero():
    cb = CarrierBridge(pass_reqs=0)
    assert not cb.enabled
    assert not cb.should_relay("GET /x", local_changes_pending=False)


def test_should_relay_blocked_by_local_changes():
    """Don't relay while local mutations are pending — the directive
    will say configHasChanges=true and the thermostat will pull our
    tree next; sending now would race that."""
    cb = CarrierBridge()
    assert not cb.should_relay("GET /x", local_changes_pending=True)


def test_should_relay_first_time_cache_miss():
    cb = CarrierBridge()
    assert cb.should_relay("GET /x", local_changes_pending=False)


def test_should_relay_respects_pass_reqs_ttl():
    cb = CarrierBridge(pass_reqs=60)
    # Plant a fresh cached entry — relay must skip until TTL elapses.
    from infinitude_proxy.carrier_bridge import CachedRelay
    cb._cache["GET /x"] = CachedRelay(
        status_code=200, body=b"ok", content_type="text/plain",
        cached_at=datetime.now(timezone.utc),
    )
    assert not cb.should_relay("GET /x", local_changes_pending=False)
    # Past the TTL: relay again.
    cb._cache["GET /x"] = CachedRelay(
        status_code=200, body=b"ok", content_type="text/plain",
        cached_at=datetime.now(timezone.utc) - timedelta(seconds=61),
    )
    assert cb.should_relay("GET /x", local_changes_pending=False)


def test_should_relay_carrier_changes_window_overrides_cache():
    """When Carrier opened the window, every request relays — the
    cache TTL doesn't apply. Matches Perl `($store->get('carrier_changes')
    or !$store->get($nk))`."""
    cb = CarrierBridge(pass_reqs=300)
    from infinitude_proxy.carrier_bridge import CachedRelay
    cb._cache["GET /x"] = CachedRelay(
        status_code=200, body=b"ok", content_type="text/plain",
        cached_at=datetime.now(timezone.utc),  # fresh cache
    )
    cb.open_carrier_changes_window()
    assert cb.should_relay("GET /x", local_changes_pending=False)


def test_carrier_changes_window_decays():
    cb = CarrierBridge(carrier_changes_window=120)
    cb.open_carrier_changes_window()
    assert cb.carrier_changes_active()
    # Force expiry by rewinding the deadline.
    cb._carrier_changes_until = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    assert not cb.carrier_changes_active()


def test_action_key_method_path_query():
    assert _action_key("GET", "/x", None) == "GET /x"
    assert _action_key("POST", "/y", "a=b") == "POST /y?a=b"
    assert _action_key("get", "/x", None) == "GET /x"  # method normalized


# ── Relay HTTP ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_relay_returns_none_when_disabled():
    """pass_reqs=0 → bridge inert; no httpx call, no cache write."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler, pass_reqs=0)
    result = await cb.relay("POST", "/systems/X/status", body=b"x")
    assert result is None
    assert seen == []


@pytest.mark.asyncio
async def test_relay_caches_response():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200, content=b"<status/>", headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler, pass_reqs=300)
    r1 = await cb.relay("GET", "/Alive", query=None)
    assert r1 is not None
    assert r1.status_code == 200
    assert r1.body == b"<status/>"
    # Second call inside TTL must hit cache, not upstream.
    r2 = await cb.relay("GET", "/Alive", query=None)
    assert r2 is r1
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_relay_opens_carrier_changes_window_on_serverHasChanges():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(
                b'<?xml version="1.0"?><status version="1.37">'
                b'<configHasChanges>false</configHasChanges>'
                b'<serverHasChanges>true</serverHasChanges>'
                b'</status>'
            ),
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler)
    assert not cb.carrier_changes_active()
    await cb.relay("POST", "/systems/2013W000855/status", body=b"data=...")
    assert cb.carrier_changes_active(), (
        "Carrier reported serverHasChanges=true; window must open"
    )


@pytest.mark.asyncio
async def test_relay_no_window_open_when_serverHasChanges_false():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<status><serverHasChanges>false</serverHasChanges></status>",
        )

    cb = _bridge_with_handler(handler)
    await cb.relay("POST", "/systems/X/status", body=b"data=...")
    assert not cb.carrier_changes_active()


@pytest.mark.asyncio
async def test_relay_swallows_network_error_returns_none():
    """A Carrier outage must not propagate to the thermostat caller —
    matches Perl's silent failure mode. The thermostat thinks its
    POST landed (we already 200'd it locally) and the relay just
    didn't happen this cycle."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated", request=request)

    cb = _bridge_with_handler(handler)
    result = await cb.relay("POST", "/systems/X/status", body=b"")
    assert result is None
    # Cache must not be poisoned with a sentinel.
    assert "POST /systems/X/status" not in cb._cache


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
    # (httpx may set its own; we just need to know we didn't pass the
    # local-hop value through.)


# ── End-to-end: southbound router invokes the bridge ──────────────────


def test_status_post_mirrors_to_carrier_when_no_local_changes():
    """A status POST with no local changes pending must trigger a
    relay to Carrier. With alpha.26's directive pass-through, the
    response sent BACK to the thermostat is Carrier's directive
    (with our local pingRate normalization), not our local stub.
    The local-stub directive is only used when the bridge is off
    or Carrier is unreachable."""
    relay_calls: list[str] = []
    carrier_directive = (
        b'<?xml version="1.0"?>\n<status version="1.37">'
        b'<configHasChanges>false</configHasChanges>'
        b'<pingRate>30</pingRate>'  # Carrier sends 30; we normalize to 12
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
    # Directive should be Carrier's body, with pingRate forced to 12.
    assert b"<pingRate>12</pingRate>" in r.content
    assert b"<pingRate>30</pingRate>" not in r.content
    assert b"<serverHasChanges>false</serverHasChanges>" in r.content
    # And the relay must have happened (boot config + status both relayed
    # — alpha.26's broader mirroring).
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


def test_config_get_returns_carrier_response_when_window_active():
    """When Carrier said serverHasChanges=true and the window is open,
    the next /systems/{id}/config GET must serve Carrier's tree —
    that's where the queued MyInfinity-app commands live. The window
    closes on first use so we don't keep returning the same tree."""
    fake_carrier_config = (
        b'<?xml version="1.0"?>\n'
        b'<config><mode>cool</mode>'
        b'<MAGIC>from-carrier</MAGIC></config>'
    )

    relay_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        relay_calls.append(f"{request.method} {request.url.path}")
        # First call: status POST, signal serverHasChanges=true so the
        # bridge opens its window.
        if request.url.path.endswith("/status"):
            return httpx.Response(
                200,
                content=(
                    b'<status><serverHasChanges>true</serverHasChanges>'
                    b'</status>'
                ),
                headers={"content-type": "application/xml"},
            )
        # Second: config GET while window is open — return the tree
        # the MyInfinity app would have queued.
        if request.url.path.endswith("/config"):
            return httpx.Response(
                200, content=fake_carrier_config,
                headers={"content-type": "application/xml"},
            )
        return httpx.Response(404)

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)

    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Status POST opens the carrier_changes window.
    client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert cb.carrier_changes_active()

    # Config GET while window is open — must return Carrier's tree.
    r = client.get("/systems/2013W000855/config")
    assert r.status_code == 200
    assert b"from-carrier" in r.content, (
        "expected Carrier's tree to be served while carrier_changes window open"
    )
    # Window must close after consumption — next GET returns local.
    assert not cb.carrier_changes_active()


async def test_config_get_in_window_replays_pending_writes_onto_carrier_tree():
    """Regression: alpha.42 user reported that an HA-side cancel-hold
    issued while the carrier_changes window is open optimistically
    clears in the UI, then "comes back" within seconds. Root cause was
    the carrier-bridge branch of GET /systems/{serial}/config serving
    Carrier's raw response body — which still carried the MyInfinity
    app's queued hold-on tree — instead of the merged tree that
    apply_config produced after replaying our pending system_hold_clear.
    The fix serializes the merged tree (Carrier ∪ pending writes) and
    marks the pending row applied, so the thermostat receives both
    Carrier's queued changes AND our HA-side mutations in one body.
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

        # Open the carrier_changes window directly. The earlier
        # status-POST → serverHasChanges=true → window-open path is
        # exercised by test_relay_opens_carrier_changes_window_on_*;
        # this test isolates the GET /config behavior with a pending
        # write present.
        cb.open_carrier_changes_window()

        # /config GET while window is open AND a pending HA-side write
        # exists. The served body must carry the merged tree, NOT
        # Carrier's raw hold-on response.
        r = client.get("/systems/2013W000855/config")
        assert r.status_code == 200
        assert b"<hold>off</hold>" in r.content, (
            "served body should reflect HA's pending cancel-hold replayed "
            "onto Carrier's tree, not Carrier's raw hold-on"
        )
        assert b"<hold>on</hold>" not in r.content
        assert b"<holdActivity>none</holdActivity>" in r.content
        # Pending row must have been marked applied by the bridge serve
        # path (mirrors the non-bridge mark_all_applied). Without this,
        # the same write would replay onto every subsequent
        # carrier_changes /config serve, never clearing.
        assert await p.unapplied_count() == 0

    await p.close()


async def test_post_clear_carrier_overwrite_protected_by_grace_window():
    """Harder version of the cancel-hold-revert bug: the HA-side
    cancel-hold has already been marked applied (pull-observed clear
    on a previous /config GET that didn't go through the bridge).
    Then Carrier opens a window with its STALE tree (still holding
    the queued app hold). Without the grace-window replay, the served
    body would revert hold to on. With pending_for_replay's grace
    window, the recently-applied system_hold_clear is re-replayed
    onto Carrier's stale tree and the cancel sticks.
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
        # First /config pull (no carrier window) marks the row applied.
        # This is what would happen on a normal HA-only write workflow:
        # thermostat sees configHasChanges=true, pulls /config, we mark
        # it applied via pull-observed-clear.
        r = client.get("/systems/2013W000855/config")
        assert r.status_code == 200
        assert await p.unapplied_count() == 0, (
            "first /config GET (no bridge) must mark the row applied"
        )
        # Row is APPLIED but still within grace.
        replay_rows = await p.pending_for_replay("2013W000855")
        assert len(replay_rows) == 1
        assert replay_rows[0].applied_at is not None
        assert replay_rows[0].kind == "system_hold_clear"

        # Now Carrier opens a fresh window and serves a stale tree
        # that still has the app's hold. The grace-window replay must
        # re-merge our cleared hold onto it.
        cb.open_carrier_changes_window()
        r = client.get("/systems/2013W000855/config")
        assert r.status_code == 200
        assert b"<hold>off</hold>" in r.content, (
            "grace-window replay should re-merge HA's cleared hold onto "
            "Carrier's stale tree, even though the row was already applied"
        )
        assert b"<hold>on</hold>" not in r.content

    await p.close()


def test_status_post_passes_carrier_configHasChanges_through():
    """The MyInfinity round-trip hinges on this: when Carrier responds
    to the relayed status POST with `configHasChanges=true`, that
    signal must reach the thermostat — otherwise the device never
    pulls the queued app commands. Without alpha.26's directive
    pass-through, the carrier_changes window opens but expires
    unused."""
    carrier_directive = (
        b'<?xml version="1.0"?>\n<status version="1.37">'
        b'<configHasChanges>true</configHasChanges>'
        b'<pingRate>20</pingRate>'
        b'<serverHasChanges>true</serverHasChanges>'
        b'</status>'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=carrier_directive,
            headers={"content-type": "application/xml"},
        )

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
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
    # Carrier's directive reached the thermostat — config-fetch
    # cycle will start.
    assert b"<configHasChanges>true</configHasChanges>" in r.content
    assert b"<serverHasChanges>true</serverHasChanges>" in r.content
    # And the carrier_changes window opened so the next config GET
    # serves Carrier's tree.
    assert cb.carrier_changes_active()


def test_config_get_schedules_followup_change_cycle():
    """After we serve Carrier's tree from the carrier_changes
    window, schedule a forced change ~60 s out so the thermostat
    re-syncs after applying the cloud commands. Mirrors Perl
    `infinitude:572` `$store->set(changes => time+60)`."""
    fake_carrier_config = b'<?xml version="1.0"?>\n<config><MAGIC>1</MAGIC></config>'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/status"):
            return httpx.Response(
                200,
                content=(
                    b'<status><serverHasChanges>true</serverHasChanges>'
                    b'</status>'
                ),
                headers={"content-type": "application/xml"},
            )
        return httpx.Response(200, content=fake_carrier_config)

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    client.post(
        "/systems/2013W000855/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    # Pre-fetch: no scheduled change yet.
    assert not cb.consume_scheduled_changes()
    cb.schedule_changes  # method exists

    r = client.get("/systems/2013W000855/config")
    assert r.status_code == 200
    assert b"MAGIC" in r.content
    # After serving Carrier's tree, the bridge has armed a future
    # changes deadline.
    assert cb._scheduled_changes_at is not None
    # Force the deadline into the past and verify consume returns True.
    cb._scheduled_changes_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    assert cb.consume_scheduled_changes() is True
    # Single-shot: subsequent consume returns False.
    assert cb.consume_scheduled_changes() is False


def test_status_post_signals_changes_when_scheduled_deadline_hit():
    """End-to-end of the scheduled-changes mechanism: simulate the
    "after Carrier config served" state by arming the deadline,
    then verify the next status POST sends configHasChanges=true to
    the thermostat (without needing a local mutation)."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Bridge would relay; respond with a benign Carrier directive.
        return httpx.Response(
            200,
            content=b'<status><configHasChanges>false</configHasChanges><serverHasChanges>false</serverHasChanges></status>',
        )

    cb = _bridge_with_handler(handler)
    # Arm an already-elapsed deadline.
    cb._scheduled_changes_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    app = create_app(store=StateStore(), carrier_bridge=cb)
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
    # Local-priority directive — has_changes=true forces this even
    # though Carrier's relayed directive would have said false.
    assert b"<configHasChanges>true</configHasChanges>" in r.content
    # And the deadline has been consumed.
    assert cb._scheduled_changes_at is None


def test_idu_odu_notifications_mirror_to_carrier():
    """Item 5: every thermostat-bound POST mirrors to Carrier so the
    cloud's view of the install matches reality. Without this, the
    MyInfinity app sees stale equipment descriptors and missed
    notifications."""
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

    # All four routes should have produced a relay.
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


def test_health_disabled_when_pass_reqs_zero():
    cb = CarrierBridge(pass_reqs=0)
    assert cb.health()["status"] == "disabled"


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
    await cb.relay("GET", "/some-unknown-path")
    h = cb.health()
    assert h["status"] == "healthy"
    assert h["consecutive_failures"] == 0


def test_healthz_endpoint_reflects_bridge_status():
    """End-to-end: /v1/healthz response shape carries the bridge's
    actual status, not the alpha.25-era hardcoded `disabled`."""
    cb = CarrierBridge()  # enabled, never attempted
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)
    r = client.get("/v1/healthz")
    assert r.status_code == 200
    cc = r.json()["components"]["carrierCloud"]
    assert cc["status"] == "unknown"
    assert cc["passReqsIntervalSeconds"] == cb._pass_reqs


def test_release_notes_falls_back_to_empty_stub_on_carrier_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated", request=request)

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)
    r = client.get("/releaseNotes/systxbbec-14.02.txt")
    assert r.status_code == 200  # Local stub kicks in.
    assert r.content == b""


def test_config_get_returns_local_tree_when_window_closed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<config><MAGIC>from-carrier</MAGIC></config>")

    cb = _bridge_with_handler(handler)
    app = create_app(store=StateStore(), carrier_bridge=cb)
    client = TestClient(app)
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Window never opened.
    r = client.get("/systems/2013W000855/config")
    assert r.status_code == 200
    # Local boot config tree, NOT Carrier's.
    assert b"from-carrier" not in r.content


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

    cb = _bridge_with_handler(handler)
    assert cb._latest_auth_headers is None  # type: ignore[attr-defined]
    await cb.relay(
        "POST", "/systems/2013W000855/status",
        headers={"Authorization": "Basic abc=", "User-Agent": "carrier"},
        body=b"data=...",
    )
    cached = cb._latest_auth_headers  # type: ignore[attr-defined]
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

    cb = _bridge_with_handler(handler)
    ok = await cb.push_config("2013W000855", b"data=fake")
    assert ok is False
    assert seen == [], "no upstream request should have been made"


@pytest.mark.asyncio
async def test_push_config_uses_cached_auth_and_correct_target():
    """push_config posts to /systems/{serial} on the upstream host
    using the cached thermostat auth, with the supplied body and
    form-urlencoded content-type — same wire shape Carrier accepts
    from a real device boot/sync POST."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    # Prime the auth cache via a normal status relay.
    await cb.relay(
        "POST", "/systems/2013W000855/status",
        headers={"Authorization": "Basic xyz="},
        body=b"data=...",
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

        def carrier_changes_active(self) -> bool:
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


def test_post_system_config_mirrors_even_when_config_dirty():
    """Side-bug fix: a thermostat-originated POST /systems/{serial}
    must mirror to Carrier regardless of `store.config_dirty`. The
    alpha.10 "skip relay on local-changes-pending" rule applies to
    *outbound polls* (status, etc.) — not to a thermostat *pushing*
    its current view, where this body IS the device's authoritative
    state and dropping the mirror loses the only natural propagation
    channel for panel-side changes. Verified live in alpha.46
    capture: panel POST #2 was silently skipped because apply_config
    had set config_dirty during replay."""
    relay_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        relay_paths.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, content=b"")

    cb = _bridge_with_handler(handler)
    store = StateStore()
    app = create_app(store=store, carrier_bridge=cb)
    client = TestClient(app)

    # Boot once so the store has state. Mirror on this first POST is
    # the precondition for the test — verify it happened.
    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    assert any(
        p == "POST /systems/2013W000855" for p in relay_paths
    ), "first boot POST should have mirrored"

    # Now force config_dirty=True via a HA mutation, then send another
    # boot-style POST. Pre-fix this second mirror was skipped (relay
    # short-circuit on local_changes_pending=True returned None
    # without any HTTP attempt); with the fix relay() proceeds to its
    # cache/TTL machinery as if config_dirty were False.
    client.put("/v1/zones/1/hold", json={"activity": "manual"})
    assert store.config_dirty is True
    relay_paths.clear()
    # Clear the bridge cache so the second POST is observably a fresh
    # outbound request, not a within-TTL cache hit. Without this we
    # can't distinguish "side-bug fixed (relay attempted, cache
    # answered)" from "side-bug present (relay skipped entirely)".
    cb._cache.clear()

    client.post(
        "/systems/2013W000855",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    assert any(
        p == "POST /systems/2013W000855" for p in relay_paths
    ), (
        "second boot POST must still mirror to Carrier despite "
        "config_dirty=True — that's the alpha.46 panel-mirror skip "
        "regression we fixed"
    )
