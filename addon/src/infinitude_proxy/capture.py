"""Debug traffic capture — tees HTTP request/response bytes to SQLite
when enabled via the debug API (`POST /v1/debug/capture/start`).

Motivation: the write-path silent-reject bug (alpha.10) surfaced
because nobody had both sides of the thermostat wire for a given
moment. Capture is off by default; the operator flips it on during
incident diagnosis or pre-cutover fixture harvests, then queries or
flushes via the debug API.

Three directions in the same table:
  - 'southbound'   — thermostat → proxy (FastAPI request cycle)
  - 'northbound'   — HA/browser → proxy (FastAPI request cycle)
  - 'carrier_out'  — proxy → carrier.com (forward-proxy passthrough;
                     emitted by an httpx event-hook, not this
                     middleware, once the passthrough route lands)

Only the middleware in this module is wired today; the carrier_out
direction is part of the schema so the future hook has a place to
land without another migration.

Implementation note: this is a raw ASGI middleware rather than a
Starlette `BaseHTTPMiddleware` because we need to read the request
body before the inner app does and replay it, which `BaseHTTPMiddleware`
handles awkwardly (it rebuilds the request but the inner stream is
already drained). Raw ASGI lets us buffer the body once and feed a
replay `receive` to the downstream app.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .persistence import Persistence

logger = logging.getLogger(__name__)

# Cap on bytes buffered per request and per response. Keeps a runaway
# upload or large static asset from ballooning memory + DB row size.
# The config dump we actually care about capturing is ~30 KB, so 1 MB
# is generous. When the cap is hit we truncate and tag the stored
# content-type suffix so consumers know the body is clipped.
MAX_BODY_BYTES = 1 * 1024 * 1024

# Paths never captured: SSE would buffer forever, healthz/docs/root
# are noise, and the debug API's own routes would trivially loop.
EXCLUDED_EXACT = frozenset({
    "/v1/healthz",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
})
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "/v1/events",          # SSE
    "/v1/debug/capture",   # the debug API itself
    "/static/",
)


@dataclass
class CaptureControl:
    """Runtime flag + config + persistence handle, shared by the
    middleware and debug API.

    Intentionally a mutable dataclass rather than a frozen Settings-
    style object: start/stop toggle the flag in-place, and lifespan
    attaches the Persistence handle once the DB is open. One instance
    per app.
    """
    enabled: bool = False
    max_rows: int = 10_000
    persistence: Persistence | None = None
    # Tally of rows we attempted to insert since process start — useful
    # for the debug status endpoint ("are we actually getting traffic
    # while capture is on?"). Incremented before the DB write attempts
    # so we can compare against actual row count to spot write failures.
    submitted: int = 0
    # Failed DB inserts (persistence error, capture raced with shutdown,
    # etc.). Surfaces silently-dropped captures on the status endpoint.
    errors: int = 0

    def start(self) -> None:
        if self.persistence is None:
            raise RuntimeError(
                "capture: persistence not attached — cannot start"
            )
        self.enabled = True

    def stop(self) -> None:
        self.enabled = False

    def attach_persistence(self, persistence: Persistence | None) -> None:
        self.persistence = persistence


def _is_excluded(path: str) -> bool:
    if path in EXCLUDED_EXACT:
        return True
    return any(path.startswith(p) for p in EXCLUDED_PREFIXES)


def _direction_for(path: str) -> str:
    """Pick a direction label from the request path.

    Rule: anything under /v1/ is northbound; everything else is a
    thermostat-facing (southbound) path. The carrier_out direction
    is emitted by the httpx hook, never by the ASGI middleware, so
    it doesn't appear here.
    """
    return "northbound" if path.startswith("/v1/") else "southbound"


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    target = name.lower()
    for k, v in headers:
        if k.lower() == target:
            try:
                return v.decode("latin-1")
            except Exception:
                return None
    return None


class CaptureMiddleware:
    """ASGI middleware that tees HTTP bytes to the SQLite capture table.

    Runs as close to the app as possible (installed last, so ordering
    is outermost first → the middleware sees bytes after other
    middleware have done their thing but before the route handler
    executes). When `control.enabled` is False the middleware is a
    straight pass-through with ~zero overhead.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        control: CaptureControl,
    ) -> None:
        self.app = app
        self.control = control

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        # Short-circuit: disabled, excluded path, or persistence hasn't
        # been attached yet (request arriving during the startup window
        # before lifespan completes). In the last case we prefer silent
        # pass-through over a 500; `control.enabled` can't be True until
        # persistence is set via `start()` anyway.
        if (
            not self.control.enabled
            or self.control.persistence is None
            or _is_excluded(path)
        ):
            await self.app(scope, receive, send)
            return

        start = time.monotonic()

        # Drain the request body up to the cap. Anything past the cap
        # is still forwarded to the app (we replay the full bytes) but
        # only the truncated prefix is what we store.
        req_body = bytearray()
        req_truncated = False
        more = True
        collected_messages: list[Message] = []
        while more:
            msg = await receive()
            collected_messages.append(msg)
            if msg["type"] == "http.request":
                chunk = msg.get("body", b"") or b""
                if len(req_body) + len(chunk) > MAX_BODY_BYTES:
                    remaining = MAX_BODY_BYTES - len(req_body)
                    if remaining > 0:
                        req_body.extend(chunk[:remaining])
                    req_truncated = True
                else:
                    req_body.extend(chunk)
                more = msg.get("more_body", False)
            elif msg["type"] == "http.disconnect":
                more = False
            else:
                more = False

        # Replay receive: hand the collected messages back to the app
        # in order, then fall through to the original receive so
        # disconnect events and keep-alive pings flow as normal.
        replay_iter = iter(collected_messages)

        async def replay_receive() -> Message:
            try:
                return next(replay_iter)
            except StopIteration:
                return await receive()

        resp_body = bytearray()
        # resp_truncated lives inside a closure-mutable dict (below) so
        # send_capture can flip it. status_code + response headers use
        # the same pattern — they're only visible from inside the send
        # callback and the surrounding dispatch needs to read them back.
        status_code_holder: dict[str, int] = {"code": 500}
        resp_headers_holder: dict[str, list[tuple[bytes, bytes]]] = {"h": []}
        resp_truncated_flag = {"x": False}

        async def send_capture(msg: Message) -> None:
            if msg["type"] == "http.response.start":
                status_code_holder["code"] = int(msg.get("status", 500))
                resp_headers_holder["h"] = list(msg.get("headers", []))
            elif msg["type"] == "http.response.body":
                chunk = msg.get("body", b"") or b""
                if not resp_truncated_flag["x"]:
                    if len(resp_body) + len(chunk) > MAX_BODY_BYTES:
                        remaining = MAX_BODY_BYTES - len(resp_body)
                        if remaining > 0:
                            resp_body.extend(chunk[:remaining])
                        resp_truncated_flag["x"] = True
                    else:
                        resp_body.extend(chunk)
            await send(msg)

        try:
            await self.app(scope, replay_receive, send_capture)
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            # Fire-and-forget the DB insert so capture overhead never
            # stretches the response path. Exceptions are logged in the
            # task body; the control counters surface silent drops.
            asyncio.create_task(
                self._record(
                    path=path,
                    query=scope.get("query_string", b"").decode("latin-1") or None,
                    method=scope.get("method", "GET"),
                    direction=_direction_for(path),
                    status_code=status_code_holder["code"],
                    req_headers=self._request_headers(scope),
                    req_body=bytes(req_body),
                    req_truncated=req_truncated,
                    resp_headers=resp_headers_holder["h"],
                    resp_body=bytes(resp_body),
                    resp_truncated=resp_truncated_flag["x"],
                    duration_ms=duration_ms,
                )
            )

    @staticmethod
    def _request_headers(scope: Scope) -> list[tuple[bytes, bytes]]:
        return list(scope.get("headers", []) or [])

    async def _record(
        self,
        *,
        path: str,
        query: str | None,
        method: str,
        direction: str,
        status_code: int,
        req_headers: list[tuple[bytes, bytes]],
        req_body: bytes,
        req_truncated: bool,
        resp_headers: list[tuple[bytes, bytes]],
        resp_body: bytes,
        resp_truncated: bool,
        duration_ms: int,
    ) -> None:
        self.control.submitted += 1
        persistence = self.control.persistence
        if persistence is None:
            # Raced with shutdown / detach. Count as an error so the
            # operator sees the drop on /v1/debug/capture/status.
            self.control.errors += 1
            return
        req_ct = _header(req_headers, b"content-type")
        resp_ct = _header(resp_headers, b"content-type")
        if req_truncated and req_ct is not None:
            req_ct = f"{req_ct}; truncated=true"
        if resp_truncated and resp_ct is not None:
            resp_ct = f"{resp_ct}; truncated=true"
        # Decode header tuples (bytes, bytes) → {str: str} for the
        # JSON column in capture_traffic. Lower-case names so any
        # downstream comparator doesn't have to handle case.
        req_headers_dict = {
            name.decode("latin-1").lower(): value.decode("latin-1")
            for (name, value) in req_headers
        }
        resp_headers_dict = {
            name.decode("latin-1").lower(): value.decode("latin-1")
            for (name, value) in resp_headers
        }
        try:
            await persistence.capture_insert(
                captured_at=time.time(),
                direction=direction,
                method=method,
                path=path,
                query=query,
                status_code=status_code,
                req_content_type=req_ct,
                req_body=req_body or None,
                resp_content_type=resp_ct,
                resp_body=resp_body or None,
                duration_ms=duration_ms,
                max_rows=self.control.max_rows,
                req_headers=req_headers_dict,
                resp_headers=resp_headers_dict,
            )
        except Exception:
            self.control.errors += 1
            logger.exception("capture: insert failed for %s %s", method, path)
