"""Bidirectional bridge between the thermostat and Carrier's cloud.

Companion to `forward_proxy.ForwardProxy`. The forward proxy handles
explicit URL-encoded requests (`/http%3A//host/...`) one-shot. This
bridge implements the *implicit* relay the legacy Perl Infinitude has
in `before_dispatch`:

  - Mirror thermostat-originated calls (status, boot/sync POST,
    notifications, idu/odu_config, equipment_events, energy) up to
    Carrier in real time. Carrier sees the device's actual traffic,
    its tree stays current with what the device reports.
  - Detect Carrier's `serverHasChanges=true` flag on relayed status
    responses. Latch a flag the southbound `/config` GET handler
    consumes — that handler then relays the thermostat's actual
    `/config` GET to Carrier (with the inbound request's fresh OAuth
    headers), applies Carrier's tree to local state, and serves
    merged. This is how Carrier-app-initiated changes reach HA.
  - Single boolean toggle `Settings.carrier_bridge` (default True).
    When disabled, the bridge is fully inert: zero outbound calls,
    all thermostat-facing endpoints serve local-only state.

────────────────────────────────────────────────────────────────────
Why this is the entire propagation surface (alpha.55)
────────────────────────────────────────────────────────────────────

Live testing 2026-05-08 verified empirically — Carrier's API uses
OAuth 1.0 with HMAC-SHA1 signatures over (method, URL, body params,
OAuth params). Three constraints follow directly from that:

  1. Nonce is single-use. Replaying a captured Authorization header
     returns `<error><message>nonce has already been used</message></error>`
     immediately, regardless of URL/method.
  2. Body is in the signed base string. Modifying the body of an
     in-flight request returns `<error><message>signature doesn't match</message></error>`.
  3. The OAuth consumer + token secrets live in thermostat firmware.
     We never see them, can't compute fresh signatures.

Net: the addon CANNOT push HA-side mutations to Carrier. Cannot
replay, cannot modify in-flight, cannot synthesize. The only outbound
calls Carrier accepts are the thermostat's own real-time signed
requests, which we relay verbatim. See
`design/LIMITATIONS.md` for the full empirical record and the
user-visible consequences of this constraint.

What we DON'T do anymore (deleted alpha.55):

  * `push_config` — synthetic POST `/systems/{serial}` to Carrier.
    Doesn't work; cached headers fail OAuth nonce check.
  * `_auth_by_route` per-route header cache. Useful only if replay
    were possible; it isn't.
  * `pull_and_apply_config` standalone background task. Same problem
    as push_config — cached `/config` GET headers 401 on replay.
    The same functional path now lives directly in southbound's
    `/config` GET handler, using the thermostat's actual fresh
    inbound headers.
  * `take_just_recovered` + catch-up push. Catch-up push fired
    `push_config` after bridge recovery. Unable to push.
  * Pending-write grace-window TTL. The 5-min replay buffer was
    designed to absorb Carrier-overrides-HA races. Carrier's actual
    behavior (re-flagging until telemetry matches its tree) means
    the grace window only postpones the override by 5 min before
    Carrier wins anyway. See LIMITATIONS for the user-facing
    documentation. Pending writes still exist for pull-observed-clear
    semantics; they just no longer survive past `mark_all_applied`.

────────────────────────────────────────────────────────────────────
Resilience contract
────────────────────────────────────────────────────────────────────

The addon must remain fully operational when Carrier is unreachable
— internet down, Carrier's API in maintenance, DNS failure, etc.

  1. Errors never propagate. Every outbound call catches network
     errors and returns None; the thermostat-facing handler always
     responds locally.
  2. Latency is bounded. Thermostat-facing endpoints respond in
     < 1 s even when Carrier has been black-holed:
       * 3 s ceiling on every outbound httpx call.
       * Circuit breaker — opens after N consecutive failures with
         exponentially-growing cooldown. Reset on first success.
       * Fire-and-forget for non-status mirrors so Carrier latency
         doesn't block the thermostat's reply.

────────────────────────────────────────────────────────────────────
Single-chokepoint outbound (alpha.51)
────────────────────────────────────────────────────────────────────

`_outbound` is the only method that touches httpx. `relay()` is a
thin wrapper that handles `local_changes_pending` short-circuit and
delegates. Every outbound call goes through one place — auth
forwarding, circuit breaker, capture, health update, access log all
happen there.
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

# Carrier's HTTPS endpoint host. The thermostat is configured with
# the API host and reaches it via DNS-overridden routing to our addon;
# we mirror to the real cloud over HTTPS.
_DEFAULT_UPSTREAM_HOST = "www.api.ing.carrier.com"

# httpx total request timeout. Tight ceiling — the thermostat is
# awaiting our reply on inline-await calls (status POST, /config GET
# fallback). Carrier responses observed live well under 1 s; 3 s
# gives headroom without making the thermostat hang on slow Carrier.
_TIMEOUT_S = 3.0

# Circuit breaker — bridge enters open state after this many
# consecutive failures, refusing relays for the cooldown duration.
_CIRCUIT_FAILURE_THRESHOLD = 3
_CIRCUIT_COOLDOWN_INITIAL_S = 30
_CIRCUIT_COOLDOWN_MAX_S = 300

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
    """One Carrier round-trip's bytes.

    Name is historic — an early alpha cached responses by request key
    with a TTL. The cache layer was deleted; the type is kept as the
    structured return value of `relay()` and the capture-traffic table
    column shape so we don't churn unrelated code.
    """
    status_code: int
    body: bytes
    content_type: str | None
    cached_at: datetime


class CarrierBridge:
    """Per-app singleton wired into the southbound router.

    `enabled=False` makes the bridge fully inert — no outbound calls,
    no httpx client opened. Use this for offline-first deployments
    where the operator wants the addon to never reach Carrier.
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        upstream_host: str = _DEFAULT_UPSTREAM_HOST,
        timeout: float = _TIMEOUT_S,
        capture_control: CaptureControl | None = None,
        circuit_failure_threshold: int = _CIRCUIT_FAILURE_THRESHOLD,
        circuit_cooldown_initial_s: int = _CIRCUIT_COOLDOWN_INITIAL_S,
        circuit_cooldown_max_s: int = _CIRCUIT_COOLDOWN_MAX_S,
    ) -> None:
        self._enabled = enabled
        self._upstream_host = upstream_host
        self._timeout = timeout
        self._capture = capture_control
        self._client: httpx.AsyncClient | None = None
        # Health stats — surfaced via /v1/healthz so the addon UI's
        # carrierCloud indicator reflects actual upstream reachability.
        self._last_success_at: datetime | None = None
        self._last_attempt_at: datetime | None = None
        self._last_error: str | None = None
        self._consecutive_failures: int = 0
        # Circuit breaker state. `_circuit_open_until` is the wall
        # time after which we'll attempt another relay. While open we
        # short-circuit `relay()` to None without touching httpx.
        self._circuit_open_until: datetime | None = None
        self._circuit_cooldown_s: int = circuit_cooldown_initial_s
        self._circuit_failure_threshold = circuit_failure_threshold
        self._circuit_cooldown_initial_s = circuit_cooldown_initial_s
        self._circuit_cooldown_max_s = circuit_cooldown_max_s
        # Latch set by `signal_carrier_has_changes` when a relayed
        # status response carried `serverHasChanges=true`. Consumed
        # by the southbound `/config` GET handler on the next
        # thermostat /config GET, which then relays the request to
        # Carrier (with the inbound request's fresh OAuth headers)
        # and applies the result to local state. Single-use — cleared
        # on first `take_pending_carrier_pull()`.
        self._pending_carrier_pull: bool = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def open(self) -> None:
        if self._client is not None or not self._enabled:
            return
        self._client = httpx.AsyncClient(
            timeout=self._timeout, follow_redirects=False,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Carrier-side change signal ──────────────────────────────────

    def signal_carrier_has_changes(self) -> None:
        """Latch that Carrier reported `serverHasChanges=true` in a
        relayed status response. Consumed by southbound `/config`
        GET on the next thermostat /config GET — that handler relays
        the inbound request to Carrier with the request's actual
        fresh OAuth headers (the only auth Carrier accepts on this
        endpoint) and applies the result to local state. Single-use:
        cleared on first `take_pending_carrier_pull()`."""
        self._pending_carrier_pull = True

    def take_pending_carrier_pull(self) -> bool:
        """Consume-on-read latch. Returns True once when changes are
        pending; subsequent calls return False until the bridge
        re-signals."""
        if self._pending_carrier_pull:
            self._pending_carrier_pull = False
            return True
        return False

    # ── Health / circuit breaker ────────────────────────────────────

    def health(self) -> dict:
        """Snapshot the bridge's reachability state for /v1/healthz.

        - `disabled` when the operator turned the bridge off.
        - `unknown` when enabled but no relay has been attempted yet.
        - `healthy` when the most recent attempt succeeded and the
          circuit breaker is closed.
        - `degraded` when consecutive failures > 0 OR the circuit
          breaker is open.
        """
        if not self._enabled:
            status = "disabled"
        elif self._last_attempt_at is None:
            status = "unknown"
        elif self._consecutive_failures > 0 or self._circuit_open():
            status = "degraded"
        else:
            status = "healthy"
        return {
            "status": status,
            "last_success_at": self._last_success_at,
            "last_attempt_at": self._last_attempt_at,
            "last_error": self._last_error,
            "consecutive_failures": self._consecutive_failures,
            "circuit_open": self._circuit_open(),
            "circuit_cooldown_s": self._circuit_cooldown_s,
            # Kept for backwards-compatible /v1/healthz consumers.
            "pass_reqs": 0,
        }

    def _circuit_open(self) -> bool:
        """True iff we're currently refusing relays due to past
        failures. Self-closing on deadline elapsed."""
        if self._circuit_open_until is None:
            return False
        if datetime.now(timezone.utc) >= self._circuit_open_until:
            self._circuit_open_until = None
            return False
        return True

    def _record_success(self) -> None:
        """Reset failure counters + circuit breaker."""
        self._consecutive_failures = 0
        self._last_error = None
        self._last_success_at = self._last_attempt_at
        self._circuit_open_until = None
        self._circuit_cooldown_s = self._circuit_cooldown_initial_s

    def _record_failure(self, error: str) -> None:
        """Increment failure counter and open the circuit breaker if
        we've crossed the threshold. Cooldown grows exponentially up
        to the cap on each consecutive open→fail cycle."""
        self._consecutive_failures += 1
        self._last_error = error
        if self._consecutive_failures >= self._circuit_failure_threshold:
            self._circuit_open_until = (
                datetime.now(timezone.utc)
                + timedelta(seconds=self._circuit_cooldown_s)
            )
            self._circuit_cooldown_s = min(
                self._circuit_cooldown_s * 2,
                self._circuit_cooldown_max_s,
            )
            logger.warning(
                "carrier_bridge: circuit opened after %d consecutive "
                "failures; cooldown=%ds (last error: %s)",
                self._consecutive_failures,
                int(
                    (self._circuit_open_until
                     - datetime.now(timezone.utc)).total_seconds()
                ),
                error,
            )

    # ── Relay (public API) ──────────────────────────────────────────

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
        """Forward one thermostat-originated request to Carrier.

        Returns the relayed response if the bridge is enabled, the
        circuit breaker is closed, and `local_changes_pending=False`
        — else returns None. Caller's headers MUST be the inbound
        thermostat request's headers (`dict(request.headers)`); the
        thermostat's OAuth signature is single-use and tied to that
        exact request, so anything else 401s.

        `local_changes_pending=True` skips the relay entirely (HA has
        a write queued; the thermostat will pull our local tree next
        and Carrier's stale view shouldn't race that).
        """
        if not self._enabled:
            return None
        if local_changes_pending:
            logger.debug(
                "carrier_bridge: skip %s %s — local changes pending",
                method.upper(), path,
            )
            return None
        return await self._outbound(
            method, path,
            query=query, body=body,
            source_headers=headers,
        )

    # ── Single-chokepoint outbound ──────────────────────────────────

    async def _outbound(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        query: str | None = None,
        source_headers: Mapping[str, str] | None = None,
    ) -> CachedRelay | None:
        """The single point through which every Carrier-bound HTTP
        call flows. `relay()` is a thin wrapper.

        Auth: `source_headers` MUST be the inbound thermostat
        request's headers. We sanitize (strip hop-by-hop, override
        Host) and forward. We do NOT cache them — Carrier's OAuth
        nonce is single-use, so cached headers always 401 on replay.
        Calls without source_headers are refused (returns None) —
        the addon has no other way to obtain valid OAuth.

        Other guards (in order, all return None):
          * bridge disabled (`enabled=False`)
          * httpx client not initialized (lifespan hasn't run)
          * circuit breaker open (recent failures)

        Health updates: 5xx → record_failure; everything else →
        record_success. 4xx is success because the round-trip itself
        worked; flapping the circuit on a single transient 401 (e.g.
        token race) would mask the working state.
        """
        if not self._enabled:
            return None
        if self._client is None:
            logger.debug(
                "carrier_bridge: skip %s %s — client not initialized",
                method.upper(), path,
            )
            return None
        if self._circuit_open():
            logger.debug(
                "carrier_bridge: skip %s %s — circuit open",
                method.upper(), path,
            )
            return None
        if source_headers is None:
            # No path forward — we can't synthesize OAuth without the
            # consumer/token secrets that live in thermostat firmware.
            # See module docstring for the full explanation.
            logger.warning(
                "carrier_bridge: skip %s %s — no source headers; "
                "addon cannot construct valid OAuth without an "
                "inbound thermostat request to relay",
                method.upper(), path,
            )
            return None

        outgoing = self._sanitize_request_headers(source_headers)
        url = f"https://{self._upstream_host}{path}"
        if query:
            url = f"{url}?{query}"

        start = time.monotonic()
        self._last_attempt_at = datetime.now(timezone.utc)
        try:
            response = await self._client.request(
                method.upper(), url,
                headers=outgoing,
                content=body or None,
            )
        except httpx.RequestError as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._record_failure(f"{type(e).__name__}: {e}")
            logger.warning(
                "relay %s %s -> error %s (%dms)",
                method.upper(), url, type(e).__name__, duration_ms,
            )
            await self._capture_failure(
                method, path, query, body, str(e), start,
                req_headers=outgoing,
            )
            return None

        duration_ms = int((time.monotonic() - start) * 1000)
        if response.status_code >= 500:
            self._record_failure(f"HTTP {response.status_code}")
        else:
            self._record_success()

        wrapped = CachedRelay(
            status_code=response.status_code,
            body=response.content,
            content_type=response.headers.get("content-type"),
            cached_at=datetime.now(timezone.utc),
        )
        logger.info(
            "relay %s %s -> %d (%dms, %d B)",
            method.upper(), url,
            response.status_code, duration_ms, len(wrapped.body),
        )
        await self._capture_success(
            method, path, query, body, response, start,
            req_headers=outgoing,
        )
        return wrapped

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
    def has_server_changes(body: bytes) -> bool:
        """True iff a relayed status response carries
        `<serverHasChanges>true</serverHasChanges>`. Public so
        southbound can decide whether to set the latch."""
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
        *,
        req_headers: Mapping[str, str] | None = None,
    ) -> None:
        if not self._should_capture():
            return
        resp_headers = {
            k.lower(): v for k, v in (response.headers.items() if response else [])
        }
        await self._capture_insert(
            method=method, path=path, query=query,
            req_body=req_body,
            status_code=response.status_code,
            resp_content_type=response.headers.get("content-type"),
            resp_body=response.content,
            duration_ms=int((time.monotonic() - start) * 1000),
            req_headers=(
                {k.lower(): v for k, v in dict(req_headers).items()}
                if req_headers is not None else None
            ),
            resp_headers=resp_headers,
        )

    async def _capture_failure(
        self,
        method: str,
        path: str,
        query: str | None,
        req_body: bytes | None,
        error: str,
        start: float,
        *,
        req_headers: Mapping[str, str] | None = None,
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
            req_headers=(
                {k.lower(): v for k, v in dict(req_headers).items()}
                if req_headers is not None else None
            ),
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
        path: str,
        query: str | None,
        req_body: bytes | None,
        status_code: int,
        resp_content_type: str | None,
        resp_body: bytes | None,
        duration_ms: int,
        req_headers: Mapping[str, str] | None = None,
        resp_headers: Mapping[str, str] | None = None,
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
                path=f"https://{self._upstream_host}{path}",
                query=query,
                status_code=status_code,
                req_content_type=(
                    dict(req_headers).get("content-type")
                    if req_headers else None
                ),
                req_body=req_body or None,
                resp_content_type=resp_content_type,
                resp_body=resp_body,
                duration_ms=duration_ms,
                max_rows=self._capture.max_rows,
                req_headers=dict(req_headers) if req_headers else None,
                resp_headers=dict(resp_headers) if resp_headers else None,
            )
        except Exception:
            self._capture.errors += 1
            logger.exception(
                "carrier_bridge: capture insert failed for %s %s",
                method, path,
            )


def _action_key(method: str, path: str, query: str | None) -> str:
    """Compose a stable identifier for a Carrier-bound request.
    Used as a label in tests and (formerly) as a cache key. Path-only
    keying mirrors upstream Perl's `$nk = $url->path->to_string`.
    """
    base = f"{method.upper()} {path}"
    if query:
        base = f"{base}?{query}"
    return base
