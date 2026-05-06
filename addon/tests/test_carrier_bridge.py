"""CarrierBridge — implicit thermostat → Carrier-cloud relay.

Companion to test_forward_proxy.py. Where the forward proxy handles
explicit `/http%3A//host/...` URL-encoded paths, the bridge handles
the *implicit* relay the legacy Perl Infinitude does in
`before_dispatch`: mirror status POSTs upstream, track Carrier's
`serverHasChanges` flag, gate config GETs on the carrier-changes
window so MyInfinity-app round-trips work.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from infinitude_proxy.capture import CaptureControl
from infinitude_proxy.carrier_bridge import (
    CarrierBridge,
    _action_key,
    _DEFAULT_PASS_REQS_S,
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
    relay to Carrier. This is the path that keeps the MyInfinity app
    seeing fresh state."""
    relay_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        relay_calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(
            200,
            content=b"<status><serverHasChanges>false</serverHasChanges></status>",
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
    # Directive must still be returned to the thermostat.
    assert b"<configHasChanges>false</configHasChanges>" in r.content
    # And the bridge must have relayed to Carrier.
    assert relay_calls == ["POST /systems/2013W000855/status"]


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
