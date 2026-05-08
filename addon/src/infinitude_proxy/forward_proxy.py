"""HTTP forward-proxy for thermostat → Carrier-cloud passthrough.

The Carrier Infinity thermostat reaches Carrier's cloud (firmware OTA,
MyInfinity app round-trips) by issuing absolute-URI HTTP requests to
its configured proxy host. Our addon receives them as paths shaped
`/http%3A//<host>/<path>` (URL-encoded scheme + colon, the HTTP
forward-proxy idiom). When the legacy Perl Infinitude was in front,
those got relayed to carrier.com via Mojo::UserAgent. Without a
relay, the proxy returns 404 and:

  - firmware update checks silently fail (thermostat keeps its current
    firmware — no crash, but stops getting updates),
  - MyInfinity-app round-trips break (the app talks to Carrier cloud,
    which relays to/from the device; without our pass-through the
    device's cloud-bound leg is severed).

This module ports the relay to httpx. A single `ForwardProxy` instance
holds an `AsyncClient`, a hostname allowlist (default: any subdomain
of carrier.com / bryant.com), and an event-hook pair that mirrors the
ASGI capture middleware so outbound calls land in the same
`capture_traffic` table with `direction='carrier_out'`. The route is
registered as a catch-all in `main.py` and gates on a `http(s)://`
prefix so it doesn't shadow the legitimate v1/southbound paths.

SSRF is the obvious concern — the thermostat is trusted, but malformed
or compromised firmware could try to coerce us into hitting arbitrary
hosts. The allowlist + scheme check are the guard. We deliberately do
not follow redirects to keep the host check authoritative.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, Request, Response

from .capture import CaptureControl

logger = logging.getLogger(__name__)

# Default allowlist: any host that *is* `carrier.com`/`bryant.com` or
# ends with `.carrier.com`/`.bryant.com`. Bryant is Carrier's
# co-branded line and shares the Infinity backend, so the same set of
# domains is reachable. Extend by passing `allowlist=` to the
# constructor if other backends are observed in the wild.
_DEFAULT_ALLOWLIST: tuple[str, ...] = ("carrier.com", "bryant.com")
_ALLOWED_SCHEMES = frozenset({"http", "https"})

# httpx total request timeout. Carrier's cloud is generally fast, but
# OTA endpoints can be slow under load. The thermostat's own retry
# cadence (~60 s on failure) gives us headroom; 30 s is the upper bound
# we'll wait before failing the relay rather than letting the addon's
# event loop block.
_TIMEOUT_S = 30.0

# Headers we strip on the way out — they describe the hop *to* our
# addon and would mislead Carrier's edge or break TLS hostname
# validation. Everything else is forwarded verbatim so the thermostat's
# auth/signing headers reach the upstream unchanged.
_HOP_BY_HOP_REQUEST = frozenset({
    "host", "connection", "proxy-connection", "te", "trailer",
    "transfer-encoding", "upgrade", "keep-alive",
})

# Headers we strip on the way back — same hop-by-hop semantics, plus
# `content-encoding` which would lie about the body if httpx already
# decompressed it.
_HOP_BY_HOP_RESPONSE = frozenset({
    "connection", "transfer-encoding", "keep-alive", "trailer",
    "upgrade", "content-encoding", "content-length",
})


class ForwardProxy:
    def __init__(
        self,
        *,
        allowlist: tuple[str, ...] | None = None,
        timeout: float = _TIMEOUT_S,
        capture_control: CaptureControl | None = None,
    ) -> None:
        self._allowlist = tuple(allowlist) if allowlist else _DEFAULT_ALLOWLIST
        self._timeout = timeout
        self._capture = capture_control
        self._client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        if self._client is not None:
            return
        # `follow_redirects=False` keeps the allowlist check on the
        # advertised target authoritative — a compromised endpoint
        # can't 302 us to an arbitrary host.
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=False,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def is_allowed(self, url: str) -> bool:
        """Allowlist check — scheme must be http/https and the host
        must be (or be a subdomain of) one of the allowed domains.
        """
        try:
            parts = urlsplit(url)
        except ValueError:
            return False
        if parts.scheme not in _ALLOWED_SCHEMES:
            return False
        host = (parts.hostname or "").lower()
        if not host:
            return False
        return any(host == d or host.endswith(f".{d}") for d in self._allowlist)

    async def forward(self, request: Request, target_url: str) -> Response:
        """Relay one request to `target_url` and return the upstream
        response wrapped as a FastAPI `Response`.

        Bodies are buffered, not streamed — the thermostat's payloads
        and OTA descriptors are small (<1 MB), and streaming would
        complicate the capture path. Switch to streaming if a real
        binary firmware push ever arrives this way.
        """
        if not self.is_allowed(target_url):
            logger.warning(
                "forward %s %s -> 403 (forbidden host)",
                request.method, target_url,
            )
            raise HTTPException(403, detail=f"forbidden host: {target_url}")
        if self._client is None:
            raise HTTPException(503, detail="forward proxy not initialized")

        method = request.method
        req_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in _HOP_BY_HOP_REQUEST
        }
        req_body = await request.body()

        start = time.monotonic()
        try:
            upstream = await self._client.request(
                method, target_url,
                headers=req_headers, content=req_body or None,
            )
        except httpx.TimeoutException as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "forward %s %s -> 504 timeout (%dms)",
                method, target_url, duration_ms,
            )
            await self._capture_failure(
                method, target_url, req_headers, req_body, 504, str(e), start
            )
            raise HTTPException(504, detail=f"upstream timeout: {e}") from e
        except httpx.RequestError as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "forward %s %s -> 502 %s (%dms)",
                method, target_url, type(e).__name__, duration_ms,
            )
            await self._capture_failure(
                method, target_url, req_headers, req_body, 502, str(e), start
            )
            raise HTTPException(502, detail=f"upstream error: {e}") from e

        duration_ms = int((time.monotonic() - start) * 1000)
        # INFO-level access log so forward-proxy traffic is visible in
        # the same log stream as inbound (uvicorn.access) and bridge
        # relays (carrier_bridge). Same shape: method url -> status (ms, bytes).
        logger.info(
            "forward %s %s -> %d (%dms, %d B)",
            method, target_url,
            upstream.status_code, duration_ms, len(upstream.content),
        )
        await self._capture_success(
            method, target_url, req_headers, req_body, upstream, duration_ms,
        )

        resp_headers = {
            k: v for k, v in upstream.headers.items()
            if k.lower() not in _HOP_BY_HOP_RESPONSE
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=resp_headers,
            media_type=upstream.headers.get("content-type"),
        )

    # ── Capture ──────────────────────────────────────────────────────────

    async def _capture_success(
        self,
        method: str,
        url: str,
        req_headers: dict[str, str],
        req_body: bytes,
        upstream: httpx.Response,
        duration_ms: int,
    ) -> None:
        if not self._should_capture():
            return
        await self._capture_insert(
            method=method, url=url,
            req_headers=req_headers, req_body=req_body,
            status_code=upstream.status_code,
            resp_content_type=upstream.headers.get("content-type"),
            resp_body=upstream.content,
            duration_ms=duration_ms,
            resp_headers={
                k.lower(): v for k, v in upstream.headers.items()
            },
        )

    async def _capture_failure(
        self,
        method: str,
        url: str,
        req_headers: dict[str, str],
        req_body: bytes,
        status_code: int,
        error: str,
        start: float,
    ) -> None:
        if not self._should_capture():
            return
        await self._capture_insert(
            method=method, url=url,
            req_headers=req_headers, req_body=req_body,
            status_code=status_code,
            resp_content_type="text/plain",
            resp_body=error.encode("utf-8"),
            duration_ms=int((time.monotonic() - start) * 1000),
            resp_headers=None,
        )

    def _should_capture(self) -> bool:
        return (
            self._capture is not None
            and self._capture.enabled
            and self._capture.persistence is not None
        )

    async def _capture_insert(
        self,
        *,
        method: str,
        url: str,
        req_headers: dict[str, str],
        req_body: bytes,
        status_code: int,
        resp_content_type: str | None,
        resp_body: bytes,
        duration_ms: int,
        resp_headers: dict[str, str] | None = None,
    ) -> None:
        assert self._capture is not None
        persistence = self._capture.persistence
        if persistence is None:
            self._capture.errors += 1
            return
        self._capture.submitted += 1
        parts = urlsplit(url)
        try:
            await persistence.capture_insert(
                captured_at=time.time(),
                direction="carrier_out",
                method=method,
                # Store full target URL as `path` so the operator can
                # tell which Carrier endpoint was hit at a glance.
                # `query` carries the query string for symmetry with
                # the inbound capture rows.
                path=f"{parts.scheme}://{parts.netloc}{parts.path}",
                query=parts.query or None,
                status_code=status_code,
                req_content_type=req_headers.get("content-type"),
                req_body=req_body or None,
                resp_content_type=resp_content_type,
                resp_body=resp_body or None,
                duration_ms=duration_ms,
                max_rows=self._capture.max_rows,
                req_headers={k.lower(): v for k, v in req_headers.items()},
                resp_headers=(
                    dict(resp_headers) if resp_headers else None
                ),
            )
        except Exception:
            self._capture.errors += 1
            logger.exception(
                "carrier_out capture insert failed for %s %s",
                method, url,
            )


def extract_target_url(request: Request) -> str | None:
    """Pull a forward-proxy target URL out of `request.url.path`.

    The thermostat encodes the absolute URI into the request line as
    `/http%3A//host/path?q=v`. After ASGI decoding, `request.url.path`
    arrives shaped `/http://host/path` (URL-decoded) and
    `request.url.query` carries the query string separately.

    Returns the reconstructed absolute URL when the path looks like a
    forward-proxy target, else None — letting the caller fall through
    to a 404 instead of accidentally relaying internal addon paths.
    """
    path = request.url.path or ""
    if path.startswith("/http://"):
        url = path[1:]  # drop the leading slash
    elif path.startswith("/https://"):
        url = path[1:]
    else:
        return None
    query = request.url.query
    if query:
        url = f"{url}?{query}"
    return url
