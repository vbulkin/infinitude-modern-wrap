"""Carrier-cloud forward-proxy — relay tests + allowlist + capture.

The thermostat reaches carrier.com via absolute-URI requests to its
configured proxy host. The legacy Perl Infinitude relayed those via
Mojo::UserAgent. `forward_proxy.ForwardProxy` is the httpx port.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from infinitude_proxy.capture import CaptureControl
from infinitude_proxy.forward_proxy import ForwardProxy, extract_target_url
from infinitude_proxy.main import create_app
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


# ── Allowlist + URL extraction ────────────────────────────────────────


def test_is_allowed_accepts_carrier_subdomains():
    fp = ForwardProxy()
    assert fp.is_allowed("http://www.ota.ing.carrier.com/releaseNotes/x.txt")
    assert fp.is_allowed("https://api.ing.carrier.com/v1/state")
    assert fp.is_allowed("http://carrier.com/")  # exact match
    assert fp.is_allowed("http://www.bryant.com/")  # bryant rebrand


def test_is_allowed_rejects_off_domain():
    fp = ForwardProxy()
    assert not fp.is_allowed("http://evil.com/")
    assert not fp.is_allowed("http://carrier.com.evil.com/")
    # "carrier" without TLD shouldn't match either
    assert not fp.is_allowed("http://carriercom/")


def test_is_allowed_rejects_non_http_schemes():
    fp = ForwardProxy()
    assert not fp.is_allowed("file:///etc/passwd")
    assert not fp.is_allowed("gopher://carrier.com/")
    assert not fp.is_allowed("ftp://www.carrier.com/")


def test_is_allowed_rejects_garbage():
    fp = ForwardProxy()
    assert not fp.is_allowed("")
    assert not fp.is_allowed("not a url")
    assert not fp.is_allowed("http://")


def test_is_allowed_custom_allowlist():
    fp = ForwardProxy(allowlist=("example.com",))
    assert fp.is_allowed("https://example.com/")
    assert fp.is_allowed("https://api.example.com/")
    assert not fp.is_allowed("https://carrier.com/")


def test_extract_target_url_handles_http_prefix():
    """ASGI decodes the encoded request line — by the time the route
    handler sees the request, `request.url.path` is `/http://host/...`
    (decoded). extract_target_url has to recognize that shape and
    return the absolute URL with the leading slash stripped."""
    # The Starlette URL helper rebuilds these the same way the request
    # object does, so we can construct one directly.
    from starlette.requests import Request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/http://www.ota.ing.carrier.com/releaseNotes/x.txt",
        "query_string": b"sn=2013W000855",
        "headers": [],
    }
    req = Request(scope)
    assert extract_target_url(req) == (
        "http://www.ota.ing.carrier.com/releaseNotes/x.txt?sn=2013W000855"
    )


def test_extract_target_url_returns_none_for_normal_paths():
    from starlette.requests import Request
    for p in ("/v1/state", "/systems/2013W000855/status", "/", "/foo/bar"):
        req = Request({
            "type": "http", "method": "GET", "path": p,
            "query_string": b"", "headers": [],
        })
        assert extract_target_url(req) is None, f"{p!r} should not match"


# ── End-to-end via FastAPI catch-all + httpx MockTransport ────────────


def _proxy_with_mock_handler(handler) -> ForwardProxy:
    """Build a ForwardProxy whose underlying httpx client is wired to
    `handler` via httpx's built-in MockTransport — no real network."""
    fp = ForwardProxy()
    fp._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(handler),
        timeout=fp._timeout,
        follow_redirects=False,
    )
    return fp


def _client_with_proxy(fp: ForwardProxy) -> TestClient:
    """Build a TestClient with the injected ForwardProxy."""
    app = create_app(store=StateStore(), forward_proxy=fp)
    return TestClient(app)


def test_get_passthrough_relays_response():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert str(request.url) == (
            "http://www.ota.ing.carrier.com/releaseNotes/systxbbec-14.02.txt"
        )
        return httpx.Response(
            200,
            content=b"# release notes for systxbbec-14.02\n",
            headers={"content-type": "text/plain"},
        )

    fp = _proxy_with_mock_handler(handler)
    client = _client_with_proxy(fp)
    r = client.get(
        "/http://www.ota.ing.carrier.com/releaseNotes/systxbbec-14.02.txt"
    )
    assert r.status_code == 200
    assert r.content == b"# release notes for systxbbec-14.02\n"
    assert r.headers["content-type"].startswith("text/plain")
    assert len(seen) == 1


def test_post_passthrough_forwards_body():
    """MyInfinity-app round-trip leg — POST body must reach upstream."""
    received_bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received_bodies.append(request.content)
        return httpx.Response(200, content=b'{"ok":true}',
                              headers={"content-type": "application/json"})

    fp = _proxy_with_mock_handler(handler)
    client = _client_with_proxy(fp)
    payload = b'{"command":"setpoint","value":72}'
    r = client.post(
        "/http://api.ing.carrier.com/v1/commands",
        content=payload,
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200
    assert received_bodies == [payload]


def test_passthrough_propagates_query_string():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=b"")

    fp = _proxy_with_mock_handler(handler)
    client = _client_with_proxy(fp)
    r = client.get(
        "/http://www.ota.ing.carrier.com/releaseNotes/x.txt"
        "?sn=2013W000855&model=systxbbec"
    )
    assert r.status_code == 200
    assert seen == [
        "http://www.ota.ing.carrier.com/releaseNotes/x.txt"
        "?sn=2013W000855&model=systxbbec"
    ]


def test_passthrough_relays_non_2xx():
    """Carrier returns 404 for unknown firmware → we relay it as 404,
    not as our own 502/error envelope."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found",
                              headers={"content-type": "text/plain"})

    fp = _proxy_with_mock_handler(handler)
    client = _client_with_proxy(fp)
    r = client.get("/http://www.ota.ing.carrier.com/missing.txt")
    assert r.status_code == 404
    assert r.content == b"not found"


def test_passthrough_blocks_off_allowlist_host():
    """Allowlist is the SSRF guard — even a well-formed http:// URL
    must 403 if the host isn't carrier/bryant."""
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("upstream must not be called for blocked host")

    fp = _proxy_with_mock_handler(handler)
    client = _client_with_proxy(fp)
    r = client.get("/http://attacker.com/secret")
    assert r.status_code == 403


def test_passthrough_returns_504_on_upstream_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated", request=request)

    fp = _proxy_with_mock_handler(handler)
    client = _client_with_proxy(fp)
    r = client.get("/http://www.ota.ing.carrier.com/x.txt")
    assert r.status_code == 504


def test_passthrough_returns_502_on_upstream_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated", request=request)

    fp = _proxy_with_mock_handler(handler)
    client = _client_with_proxy(fp)
    r = client.get("/http://www.ota.ing.carrier.com/x.txt")
    assert r.status_code == 502


def test_unmatched_path_falls_through_to_404():
    """The catch-all must not shadow normal 404s for non-passthrough
    paths. Without this guarantee, a typo in the v1 surface would
    silently become a forward-proxy attempt."""
    fp = ForwardProxy()  # no client — would crash if hit
    client = _client_with_proxy(fp)
    r = client.get("/v1/this-does-not-exist")
    assert r.status_code == 404


# ── Capture integration ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_passthrough_writes_carrier_out_capture_row():
    """When capture is on, forwarded calls land in the same SQLite
    table the inbound middleware writes to, with direction=carrier_out.
    This is the symmetric-visibility property promised in the
    capture.py module docstring."""
    persistence = await Persistence.open(":memory:")
    try:
        control = CaptureControl(max_rows=100, persistence=persistence)
        control.start()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, content=b"firmware-blob",
                headers={"content-type": "application/octet-stream"},
            )

        fp = ForwardProxy(capture_control=control)
        fp._client = httpx.AsyncClient(  # type: ignore[attr-defined]
            transport=httpx.MockTransport(handler),
            timeout=fp._timeout,
            follow_redirects=False,
        )

        # Use a Starlette Request directly — bypassing the FastAPI
        # plumbing keeps the test focused on the capture path.
        from starlette.requests import Request as StarletteRequest

        async def empty_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/http://www.ota.ing.carrier.com/x.txt",
            "query_string": b"",
            "headers": [],
        }
        req = StarletteRequest(scope, receive=empty_receive)
        target = extract_target_url(req)
        assert target is not None
        await fp.forward(req, target)

        rows = await persistence.capture_list(limit=10, direction="carrier_out")
        assert len(rows) == 1
        row = rows[0]
        assert row["direction"] == "carrier_out"
        assert row["method"] == "GET"
        assert row["path"] == "http://www.ota.ing.carrier.com/x.txt"
        assert row["status_code"] == 200
        assert control.submitted == 1
        assert control.errors == 0
    finally:
        await persistence.close()
