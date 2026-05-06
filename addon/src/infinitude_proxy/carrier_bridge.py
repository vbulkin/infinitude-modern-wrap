"""Bidirectional bridge between the thermostat and Carrier's cloud.

Companion to `forward_proxy.ForwardProxy`. The forward proxy handles
explicit URL-encoded requests (`/http%3A//host/...`) one-shot. This
bridge implements the *implicit* relay the legacy Perl Infinitude has
in `before_dispatch`:

  - Mirror thermostat status posts up to Carrier so Carrier's view of
    the device matches reality. Without this, app-side state in the
    MyInfinity app stays stale.
  - Track Carrier's `serverHasChanges` flag and open a 120 s
    carrier-changes window when it flips on. While the window is open
    the next `/systems/{id}/config` GET serves Carrier's tree (which
    carries the queued app-initiated changes) instead of the local
    one, so app commands actually reach the device.
  - Cache by request key with `pass_reqs` TTL (default 5 min) so we
    don't hammer Carrier on every poll. Cache bypassed while the
    carrier-changes window is open or while local mutations are
    pending.

Decision points mirror Perl `infinitude:259`:
    if pass_reqs and !local_changes and (carrier_changes or !cached):
        relay; cache response; stash for downstream handlers.

Storage is in-memory — restart resets both the cache and the windows.
The pass_reqs default (300 s) and carrier_changes window (120 s)
match upstream defaults; both are configurable on construction.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping

import httpx

from .capture import CaptureControl

logger = logging.getLogger(__name__)

# Carrier's HTTPS endpoint hosts. The thermostat is configured with
# the API host and reaches it via DNS-overridden routing to our addon;
# we mirror to the real cloud over HTTPS. The bryant.com mirror is
# kept as a fallback for Bryant-branded units.
_DEFAULT_UPSTREAM_HOST = "www.api.ing.carrier.com"

# Default pass_reqs cadence (seconds). Matches the upstream default
# `60*5` from `infinitude:47`. Set to 0 to disable mirroring entirely.
_DEFAULT_PASS_REQS_S = 300

# Length of the carrier-changes window opened when Carrier reports
# `serverHasChanges=true` in a relayed status POST. Matches upstream
# `$store->set(carrier_changes => time, 120)` in `infinitude:610`.
_DEFAULT_CARRIER_CHANGES_S = 120

# httpx total request timeout. Carrier's API is generally fast; we
# bound it so a hung relay can't block thermostat replies.
_TIMEOUT_S = 10.0

# `serverHasChanges` extraction — small XML fragment, no need for a
# full parse (and parsing would couple us to the response shape).
_SERVER_HAS_CHANGES_RE = re.compile(
    rb"<serverHasChanges>\s*(true|false)\s*</serverHasChanges>",
    re.IGNORECASE,
)

# Hop-by-hop request headers we strip on the way out — they describe
# the local hop and would mislead Carrier's TLS/auth or break HTTP/2.
_HOP_BY_HOP_REQUEST = frozenset({
    "host", "connection", "proxy-connection", "te", "trailer",
    "transfer-encoding", "upgrade", "keep-alive",
    # Strip content-length so httpx can recompute it for the body
    # we're forwarding.
    "content-length",
})


@dataclass(frozen=True)
class CachedRelay:
    """One Carrier round-trip's bytes, kept by request key."""
    status_code: int
    body: bytes
    content_type: str | None
    cached_at: datetime


def _action_key(method: str, path: str, query: str | None) -> str:
    """Cache key — method + path + query (no Host since we always
    relay to the same upstream host). Path-only would collide
    cross-method; mirroring upstream's `nk = path` keying because
    in practice GET and POST never share a path."""
    base = f"{method.upper()} {path}"
    if query:
        base = f"{base}?{query}"
    return base


class CarrierBridge:
    """Per-app singleton wired into the southbound router.

    `pass_reqs=0` disables the bridge entirely — use this when the
    operator wants the addon's local processing to be authoritative
    and never reaches out to Carrier (offline-first deployments).
    """

    def __init__(
        self,
        *,
        upstream_host: str = _DEFAULT_UPSTREAM_HOST,
        pass_reqs: int = _DEFAULT_PASS_REQS_S,
        carrier_changes_window: int = _DEFAULT_CARRIER_CHANGES_S,
        timeout: float = _TIMEOUT_S,
        capture_control: CaptureControl | None = None,
    ) -> None:
        self._upstream_host = upstream_host
        self._pass_reqs = pass_reqs
        self._window_seconds = carrier_changes_window
        self._timeout = timeout
        self._capture = capture_control
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, CachedRelay] = {}
        self._carrier_changes_until: datetime | None = None
        # Future-timestamp scheduled-changes flag — set after we serve
        # Carrier's tree from `/systems/{id}/config` to force a follow-up
        # config-fetch cycle ~60 s later, mirroring Perl
        # `infinitude:572`'s `$store->set(changes => time+60)`. The next
        # status POST consumes it once `now > scheduled_at`.
        self._scheduled_changes_at: datetime | None = None

    @property
    def enabled(self) -> bool:
        return self._pass_reqs > 0

    async def open(self) -> None:
        if self._client is not None or not self.enabled:
            return
        self._client = httpx.AsyncClient(
            timeout=self._timeout, follow_redirects=False,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Public state accessors ───────────────────────────────────────

    def carrier_changes_active(self) -> bool:
        """True iff Carrier signalled `serverHasChanges` recently and
        the 120 s window hasn't elapsed."""
        until = self._carrier_changes_until
        return until is not None and datetime.now(timezone.utc) < until

    def open_carrier_changes_window(self) -> None:
        self._carrier_changes_until = (
            datetime.now(timezone.utc) + timedelta(seconds=self._window_seconds)
        )

    def close_carrier_changes_window(self) -> None:
        self._carrier_changes_until = None

    def get_cached(self, key: str) -> CachedRelay | None:
        return self._cache.get(key)

    def schedule_changes(self, seconds: int = 60) -> None:
        """Arm the delayed-changes flag — at `now + seconds` and beyond,
        the next call to `consume_scheduled_changes()` returns True.
        Mirrors Perl's `$store->set(changes => time+60)` after a Carrier
        config has been served. Idempotent: calling again replaces the
        deadline rather than queuing multiple."""
        self._scheduled_changes_at = (
            datetime.now(timezone.utc) + timedelta(seconds=seconds)
        )

    def consume_scheduled_changes(self) -> bool:
        """Atomic: return True iff a scheduled-changes deadline exists
        and has elapsed; clear it on success. Returns False otherwise.

        Called from the status-POST handler. The semantics match Perl
        `infinitude:589`: `if ($changes =~ /\\d+/) { $changes = (time>$changes) ? 'true' : '' }`
        followed by `$store->set(changes=>'')` on consumption.
        """
        deadline = self._scheduled_changes_at
        if deadline is None:
            return False
        if datetime.now(timezone.utc) < deadline:
            return False
        self._scheduled_changes_at = None
        return True

    # ── Mirror flow ──────────────────────────────────────────────────

    def should_relay(self, action_key: str, *, local_changes_pending: bool) -> bool:
        """Decision matches `infinitude:266`:

            pass_reqs enabled
            AND no local changes pending (don't leak in-flight state
                to Carrier; we want the thermostat to pull our local
                tree first)
            AND (carrier_changes window open OR cache miss / stale)
        """
        if not self.enabled:
            return False
        if local_changes_pending:
            return False
        if self.carrier_changes_active():
            return True
        cached = self._cache.get(action_key)
        if cached is None:
            return True
        age = (datetime.now(timezone.utc) - cached.cached_at).total_seconds()
        return age >= self._pass_reqs

    async def relay(
        self,
        method: str,
        path: str,
        *,
        query: str | None = None,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
        local_changes_pending: bool = False,
    ) -> CachedRelay | None:
        """Forward one request to Carrier and cache the response.

        Returns the relayed (or cached) `CachedRelay` if mirroring was
        eligible, else None — callers fall back to local-only handling.

        Network failures return None and are logged at WARNING; we
        deliberately do *not* propagate them to the thermostat caller,
        matching the Perl behavior where a Carrier outage is
        transparent to the device.
        """
        key = _action_key(method, path, query)
        if not self.should_relay(key, local_changes_pending=local_changes_pending):
            cached_hit = self._cache.get(key)
            # Log at DEBUG so the operator can ask "why did/didn't we
            # relay?" without the per-poll INFO noise. Three reasons
            # short-circuit a relay: bridge disabled (pass_reqs=0),
            # local mutation pending, or cache hit within TTL.
            if not self.enabled:
                reason = "disabled (pass_reqs=0)"
            elif local_changes_pending:
                reason = "local-changes-pending"
            elif self.carrier_changes_active():
                reason = "window-open (should not happen — bug)"
            elif cached_hit is not None:
                age = (
                    datetime.now(timezone.utc) - cached_hit.cached_at
                ).total_seconds()
                reason = f"cache-hit age={age:.0f}s ttl={self._pass_reqs}s"
            else:
                reason = "unknown"
            logger.debug(
                "skip %s %s — %s%s",
                method.upper(), path, reason,
                f" (returning cached status={cached_hit.status_code})"
                if cached_hit is not None else "",
            )
            return cached_hit
        if self._client is None:
            logger.debug(
                "skip %s %s — client not initialized",
                method.upper(), path,
            )
            return None

        url = f"https://{self._upstream_host}{path}"
        if query:
            url = f"{url}?{query}"

        outgoing_headers = self._sanitize_request_headers(headers or {})

        start = time.monotonic()
        try:
            response = await self._client.request(
                method.upper(), url,
                headers=outgoing_headers,
                content=body or None,
            )
        except httpx.RequestError as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            # Match the access-log shape (method url -> status (Nms))
            # so failures sit alongside successes when the operator
            # tail's the addon log.
            logger.warning(
                'relay %s %s -> error %s (%dms)',
                method.upper(), url, type(e).__name__, duration_ms,
            )
            await self._capture_failure(method, path, query, body, str(e), start)
            return None

        duration_ms = int((time.monotonic() - start) * 1000)
        cached = CachedRelay(
            status_code=response.status_code,
            body=response.content,
            content_type=response.headers.get("content-type"),
            cached_at=datetime.now(timezone.utc),
        )
        self._cache[key] = cached

        # Per-request access-log — INFO level, formatted like uvicorn's
        # access log so outbound Carrier traffic is visible in the
        # same `journalctl`/Apps log stream as inbound thermostat
        # traffic. Body length helps spot empty / truncated responses
        # at a glance.
        logger.info(
            'relay %s %s -> %d (%dms, %d B)',
            method.upper(), url,
            response.status_code, duration_ms, len(cached.body),
        )

        # The carrier-changes window is opened on Carrier saying
        # `serverHasChanges=true` in a relayed STATUS post. Don't
        # extend on cache hits — the trigger is a fresh signal, not a
        # stored one.
        if path.endswith("/status") and self._has_server_changes(cached.body):
            self.open_carrier_changes_window()
            logger.info(
                "opened carrier_changes window (%ds) on serverHasChanges=true",
                self._window_seconds,
            )

        await self._capture_success(method, path, query, body, response, start)
        return cached

    # ── Internal helpers ─────────────────────────────────────────────

    def _sanitize_request_headers(
        self, headers: Mapping[str, str]
    ) -> dict[str, str]:
        # Forward auth, content-type, accept, etc. — strip hop-by-hop.
        # Override Host to the upstream so TLS SNI matches.
        out = {
            k: v for k, v in headers.items()
            if k.lower() not in _HOP_BY_HOP_REQUEST
        }
        out["host"] = self._upstream_host
        return out

    @staticmethod
    def _has_server_changes(body: bytes) -> bool:
        m = _SERVER_HAS_CHANGES_RE.search(body or b"")
        return m is not None and m.group(1).lower() == b"true"

    # ── Capture (mirrors forward_proxy capture path) ─────────────────

    async def _capture_success(
        self,
        method: str,
        path: str,
        query: str | None,
        req_body: bytes | None,
        response: httpx.Response,
        start: float,
    ) -> None:
        if not self._should_capture():
            return
        await self._capture_insert(
            method=method, path=path, query=query,
            req_body=req_body,
            status_code=response.status_code,
            resp_content_type=response.headers.get("content-type"),
            resp_body=response.content,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def _capture_failure(
        self,
        method: str,
        path: str,
        query: str | None,
        req_body: bytes | None,
        error: str,
        start: float,
    ) -> None:
        if not self._should_capture():
            return
        await self._capture_insert(
            method=method, path=path, query=query,
            req_body=req_body,
            status_code=502,
            resp_content_type="text/plain",
            resp_body=error.encode("utf-8"),
            duration_ms=int((time.monotonic() - start) * 1000),
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
        path: str,
        query: str | None,
        req_body: bytes | None,
        status_code: int,
        resp_content_type: str | None,
        resp_body: bytes | None,
        duration_ms: int,
    ) -> None:
        assert self._capture is not None
        persistence = self._capture.persistence
        if persistence is None:
            self._capture.errors += 1
            return
        self._capture.submitted += 1
        try:
            await persistence.capture_insert(
                captured_at=time.time(),
                direction="carrier_out",
                method=method,
                # Store the full target URL so the operator can tell
                # bridge-relayed traffic apart from forward-proxy
                # at a glance — both share direction='carrier_out'.
                path=f"https://{self._upstream_host}{path}",
                query=query,
                status_code=status_code,
                req_content_type=None,
                req_body=req_body or None,
                resp_content_type=resp_content_type,
                resp_body=resp_body,
                duration_ms=duration_ms,
                max_rows=self._capture.max_rows,
            )
        except Exception:
            self._capture.errors += 1
            logger.exception(
                "carrier_bridge: capture insert failed for %s %s",
                method, path,
            )
