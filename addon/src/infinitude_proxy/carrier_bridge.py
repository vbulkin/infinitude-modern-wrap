"""Bidirectional bridge between the thermostat and Carrier's cloud.

Companion to `forward_proxy.ForwardProxy`. The forward proxy handles
explicit URL-encoded requests (`/http%3A//host/...`) one-shot. This
bridge implements the *implicit* relay the legacy Perl Infinitude has
in `before_dispatch`:

  - Mirror thermostat status posts up to Carrier so Carrier's view of
    the device matches reality. Without this, app-side state in the
    MyInfinity app stays stale.
  - Detect Carrier's `serverHasChanges=true` flag in relayed status
    responses and proactively pull `/systems/{id}/config` from Carrier
    so HA picks up app-initiated changes within one telemetry tick
    instead of waiting for a thermostat re-fetch cycle.

Storage is in-memory — restart resets bridge state. Configuration is
a single boolean: `Settings.carrier_bridge` (default True). When
disabled, the bridge is fully inert: zero outbound calls, all
thermostat-facing endpoints serve local-only state.

────────────────────────────────────────────────────────────────────
Why we no longer throttle / cache (alpha.48 simplification)
────────────────────────────────────────────────────────────────────

Earlier alphas (≤ alpha.47) carried a `pass_reqs` cadence (default
120 s) keyed by request path that gated outbound relays — modeled
on Perl Infinitude's `pass_reqs`. The original purpose was to limit
how often the proxy could ask Carrier "is anything queued?" so we
didn't hammer the API. That made sense in Perl because there was no
push-up channel for HA mutations: every Carrier round-trip risked
re-asserting stale state, so throttling was bug mitigation.

We deleted that throttle (and the matching `_cache`,
`carrier_changes_until` window, and `_scheduled_changes_at` future-
flag mechanisms) when we landed two new pieces:
  * `push_config` (alpha.47) — every HA mutation fires a synthetic
    boot-style POST to Carrier so Carrier learns about it within
    seconds. Carrier's tree is now always at-or-ahead of ours.
  * Proactive pull (`pull_and_apply_config`, this alpha) — when we
    see Carrier signal `serverHasChanges=true`, we pull `/config`
    from Carrier ourselves and apply it to local state. The
    thermostat's next `GET /config` then serves the merged tree
    naturally; no carrier-changes window needed.

Carrier's existing `pingRate` directive *already* lets it throttle
the device-side cadence end-to-end; layering a second proxy-side
throttle was actively defeating that signal (we were stripping
Carrier's pingRate and forcing 12 s, even when Carrier asked for 30 s
during their maintenance windows). After alpha.48 we forward
Carrier's pingRate verbatim in clean state and only override when
we have local pending writes (DIRTY=20).

────────────────────────────────────────────────────────────────────
Asymmetry that necessitated push_config (carried over from alpha.47)
────────────────────────────────────────────────────────────────────

Carrier learns about device-side config from one upstream path: the
thermostat's `POST /systems/{serial}` boot/sync POST. The thermostat
does this on actual boot AND on its own internal cadence after
panel-originated changes. Our bridge mirrors that POST to
api.ing.carrier.com. This is how panel changes propagate upstream.

The thermostat decides when to re-POST based on whether it considers
the change *device-originated* — a panel touch counts; receiving a
config tree from `GET /systems/{serial}/config` (which our addon
serves) does NOT, because as far as the thermostat can tell that
config came from upstream and Carrier already knows about it. From
the thermostat's perspective there is no wire-level distinction
between a config we built from an HA mutation and one Carrier
queued via the MyInfinity app — both arrive over the same `GET
/config` channel.

Result without `push_config`: HA mutations land in our local tree,
get pulled by the thermostat on the next /config GET, and stop
there. Carrier never hears about them. The `push_config` method
synthesizes the exact wire shape the thermostat would have produced
after a panel change, using auth headers cached from the most
recent inbound thermostat request, so Carrier's tree matches HA's
within ~1 s of every HA mutation.

────────────────────────────────────────────────────────────────────
Resilience contract (alpha.48)
────────────────────────────────────────────────────────────────────

The addon must remain fully operational when Carrier is unreachable
— internet down, Carrier's API in maintenance, DNS failure, etc.
Concretely:

  1. Errors never propagate. Every outbound call (`relay`,
     `push_config`, `pull_and_apply_config`) catches network errors
     and returns False/None; the calling thermostat handler always
     responds locally.

  2. Latency is bounded. Thermostat-facing endpoints respond in
     < 1 s even when Carrier has been black-holed for hours, via:
       * A 3 s ceiling on every outbound httpx call (`_TIMEOUT_S`).
       * A circuit breaker that short-circuits relay attempts after
         N consecutive failures, opening for an exponentially-growing
         cooldown up to 5 min. Reset on first success.
       * Fire-and-forget for non-status mirrors (notifications,
         idu_config, etc.) — those don't need Carrier's response.

  3. Catch-up on recovery. When the bridge transitions from failing
     to succeeding, we fire one synthetic `push_config` carrying the
     current local tree, so any HA mutations that occurred during
     the outage propagate to Carrier without operator intervention.
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

# httpx total request timeout. Tight ceiling — thermostat is awaiting
# our reply on inline-await calls (status POST, /config GET fallback).
# Carrier responses observed live well under 1 s; 3 s gives headroom
# without making the thermostat hang on a slow Carrier.
_TIMEOUT_S = 3.0

# Circuit breaker — bridge enters open state after this many
# consecutive failures, refusing relays for the cooldown duration.
# Each open/re-fail extends the cooldown exponentially up to the cap,
# so a sustained Carrier outage costs us at most one timeout per
# `_CIRCUIT_COOLDOWN_MAX_S`, not one per call.
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

    Name is historic — alpha.0–47 cached these by request key with a
    `pass_reqs` TTL. Cache layer was deleted in alpha.48; the type
    is kept as the structured return value of `relay()` and the
    capture-traffic table column shape so we don't churn unrelated
    code.
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
        # Latch flipped when a relay succeeds after a failure streak;
        # consumed by the caller (`southbound.post_telemetry`) to fire
        # a catch-up `push_config` so any HA mutations that happened
        # during the outage propagate to Carrier without operator
        # intervention. Single-use semantics: set on transition,
        # cleared by `take_just_recovered()`.
        self._just_recovered: bool = False
        # Circuit breaker state. `_circuit_open_until` is the wall
        # time after which we'll attempt another relay. While open we
        # short-circuit `relay()` to None without touching httpx.
        # `_circuit_cooldown_s` is the current cooldown duration; it
        # doubles on each open→fail until capped at the max.
        self._circuit_open_until: datetime | None = None
        self._circuit_cooldown_s: int = circuit_cooldown_initial_s
        self._circuit_failure_threshold = circuit_failure_threshold
        self._circuit_cooldown_initial_s = circuit_cooldown_initial_s
        self._circuit_cooldown_max_s = circuit_cooldown_max_s
        # Latest auth-relevant request headers seen on a thermostat-
        # originated relay. Used by `push_config` so HA-driven config
        # updates can be POSTed upstream as if they came from the
        # device itself. Headers are stale-tolerant: Carrier accepts
        # them as long as the most recent thermostat request landed
        # within their TTL (which is at least the status-POST cadence,
        # 12-30 s — far less than any reasonable token lifetime). On
        # cold start there is no cache and `push_config` is a no-op
        # until the thermostat's first relayed request lands.
        self._latest_auth_headers: dict[str, str] | None = None

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

    # ── Health / circuit breaker ────────────────────────────────────

    def health(self) -> dict:
        """Snapshot the bridge's reachability state for /v1/healthz.

        - `disabled` when the operator turned the bridge off.
        - `unknown` when enabled but no relay has been attempted yet
          (process just started, no thermostat traffic yet).
        - `healthy` when the most recent attempt succeeded and the
          circuit breaker is closed.
        - `degraded` when consecutive failures > 0 OR the circuit
          breaker is open. The /v1/healthz overall status downgrades
          to `degraded` whenever any component is in this state.
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
            # Kept for backwards-compatible /v1/healthz consumers
            # that read `pass_reqs`. Always 0 now (no throttle).
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
        """Reset failure counters + circuit breaker. Latches
        `_just_recovered` if we transitioned from a failing state so
        a caller can fire a catch-up push (consumed via
        `take_just_recovered`)."""
        was_failing = (
            self._consecutive_failures > 0 or self._circuit_open_until is not None
        )
        self._consecutive_failures = 0
        self._last_error = None
        self._last_success_at = self._last_attempt_at
        self._circuit_open_until = None
        self._circuit_cooldown_s = self._circuit_cooldown_initial_s
        if was_failing:
            self._just_recovered = True
            logger.info(
                "carrier_bridge: recovered (consecutive failures cleared); "
                "next caller should fire a catch-up push to resync upstream",
            )

    def take_just_recovered(self) -> bool:
        """Atomic check-and-clear of the recovery latch. Returns True
        once after the bridge transitions failing → succeeding;
        subsequent calls return False until the next failure streak."""
        if self._just_recovered:
            self._just_recovered = False
            return True
        return False

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
            # Double the cooldown for the *next* open → fail cycle,
            # so a persistent outage doesn't keep retrying every
            # `_CIRCUIT_COOLDOWN_INITIAL_S`. Capped at the max.
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

    # ── Mirror flow ──────────────────────────────────────────────────

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
        """Forward one request to Carrier and return the response.

        Returns the relayed response if the bridge is enabled, the
        circuit breaker is closed, and `local_changes_pending=False`
        — else returns None and the caller falls back to local-only
        handling. Network failures return None and are logged at
        WARNING; we deliberately do *not* propagate them to the
        caller, matching the Perl behavior where a Carrier outage is
        transparent to the device.

        `local_changes_pending`: pass True only for thermostat-facing
        outbound polls where HA has a write queued (the thermostat
        will pull our local tree next, and Carrier's stale view
        shouldn't race that). Pass False for thermostat-originated
        POSTs (the body IS the device's authoritative state — see
        the alpha.46 panel-mirror-skip side bug for why this matters).
        """
        if not self._enabled:
            return None
        if local_changes_pending:
            logger.debug(
                "carrier_bridge: skip %s %s — local changes pending",
                method.upper(), path,
            )
            return None
        if self._circuit_open():
            logger.debug(
                "carrier_bridge: skip %s %s — circuit open",
                method.upper(), path,
            )
            return None
        if self._client is None:
            logger.debug(
                "carrier_bridge: skip %s %s — client not initialized",
                method.upper(), path,
            )
            return None

        url = f"https://{self._upstream_host}{path}"
        if query:
            url = f"{url}?{query}"

        outgoing_headers = self._sanitize_request_headers(headers or {})

        # Cache the sanitized auth set for `push_config`. We rotate on
        # every relay (every status POST = every 12-30 s during normal
        # operation) so Carrier never sees auth older than one cadence
        # tick. Cached BEFORE we send so a 401 here doesn't blank the
        # last known-good set — push_config will discover the same 401
        # and log; the next status POST gives us fresh auth.
        self._latest_auth_headers = dict(outgoing_headers)

        start = time.monotonic()
        self._last_attempt_at = datetime.now(timezone.utc)
        try:
            response = await self._client.request(
                method.upper(), url,
                headers=outgoing_headers,
                content=body or None,
            )
        except httpx.RequestError as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._record_failure(f"{type(e).__name__}: {e}")
            logger.warning(
                'relay %s %s -> error %s (%dms)',
                method.upper(), url, type(e).__name__, duration_ms,
            )
            await self._capture_failure(method, path, query, body, str(e), start)
            return None

        # 5xx from Carrier is also a failure for health purposes (their
        # API is up but returning errors); 4xx is application-level
        # (we sent something they didn't like) and counts as success
        # since the round-trip itself worked.
        if response.status_code >= 500:
            self._record_failure(f"HTTP {response.status_code}")
        else:
            self._record_success()

        duration_ms = int((time.monotonic() - start) * 1000)
        relay_response = CachedRelay(
            status_code=response.status_code,
            body=response.content,
            content_type=response.headers.get("content-type"),
            cached_at=datetime.now(timezone.utc),
        )

        # Per-request access-log — INFO level, formatted like uvicorn's
        # access log so outbound Carrier traffic is visible in the
        # same `journalctl`/Apps log stream as inbound thermostat
        # traffic.
        logger.info(
            'relay %s %s -> %d (%dms, %d B)',
            method.upper(), url,
            response.status_code, duration_ms, len(relay_response.body),
        )

        await self._capture_success(method, path, query, body, response, start)
        return relay_response

    async def push_config(self, serial: str, body: bytes) -> bool:
        """Synthesize a thermostat-style boot POST so Carrier learns
        about an HA-originated config change.

        See the module docstring for *why* this exists. In short: when
        a config change is initiated at the thermostat panel, the
        thermostat naturally re-POSTs `/systems/{serial}` upstream and
        our `_bridge_mirror` carries that to Carrier. When the change
        is initiated in HA, the thermostat consumes our local tree via
        `GET /config` and (correctly, from its perspective) does NOT
        re-POST upstream — it can't distinguish HA-served bytes from
        Carrier-served bytes, so it treats both as already-known to
        Carrier. This method plugs that gap by emitting the wire-shape
        the panel-originated POST would have produced.

        Body is the form-encoded `<system version="1.7"><config>...
        </config></system>` shape that the thermostat sends — see
        `parser.serialize_system_post_body`.

        Returns True iff Carrier replied 2xx. Failures (network errors,
        4xx auth, 5xx) are logged but never propagated to the caller —
        HA's mutation has already landed locally; the upstream sync
        is a best-effort consistency layer, not the success criterion
        for the user-visible action.

        No-ops in four cases:
          * bridge disabled by operator (`enabled=False`).
          * httpx client not yet opened (lifespan hasn't run).
          * circuit breaker is open (recent failures).
          * No thermostat auth headers cached yet (cold start before
            the first inbound thermostat request).
        Each is logged so the operator can tell why a push didn't
        happen.
        """
        if not self._enabled:
            logger.debug("push_config: bridge disabled")
            return False
        if self._client is None:
            logger.debug("push_config: httpx client not initialized")
            return False
        if self._circuit_open():
            logger.debug("push_config: circuit open; deferring upstream sync")
            return False
        if self._latest_auth_headers is None:
            # This is genuinely common during the first ~30 s of
            # process lifetime, before the thermostat's first status
            # POST. Once the cache populates, every subsequent push
            # works. WARNING (not DEBUG) so a *persistent* miss is
            # visible — that would mean the thermostat isn't reaching
            # us at all, which is a bigger problem than a delayed push.
            logger.warning(
                "push_config: no thermostat auth headers cached yet "
                "(serial=%s, body=%d B); deferring upstream sync",
                serial, len(body),
            )
            return False

        path = f"/systems/{serial}"
        url = f"https://{self._upstream_host}{path}"
        outgoing_headers = self._sanitize_request_headers(self._latest_auth_headers)
        outgoing_headers["content-type"] = "application/x-www-form-urlencoded"

        start = time.monotonic()
        self._last_attempt_at = datetime.now(timezone.utc)
        try:
            response = await self._client.request(
                "POST", url,
                headers=outgoing_headers,
                content=body,
            )
        except httpx.RequestError as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._record_failure(f"push_config {type(e).__name__}: {e}")
            logger.warning(
                "push_config %s -> error %s (%dms)",
                url, type(e).__name__, duration_ms,
            )
            await self._capture_failure("POST", path, None, body, str(e), start)
            return False

        duration_ms = int((time.monotonic() - start) * 1000)
        if 200 <= response.status_code < 300:
            self._record_success()
        elif response.status_code >= 500:
            self._record_failure(f"push_config HTTP {response.status_code}")

        logger.info(
            "push %s %s -> %d (%dms, %d B body)",
            "POST", url, response.status_code, duration_ms, len(body),
        )
        await self._capture_success("POST", path, None, body, response, start)
        return 200 <= response.status_code < 300

    async def pull_and_apply_config(self, serial: str, store) -> bool:
        """Proactively fetch Carrier's `/config` tree and apply it
        locally.

        Triggered by `southbound.post_telemetry` when a relayed status
        response carried `serverHasChanges=true`. This collapses the
        legacy "carrier_changes window" mechanism into a direct state
        apply: instead of waiting for the thermostat to do its next
        `GET /config`, relaying that to Carrier, and merging in-band,
        we pull from Carrier ourselves on the same status-POST tick
        and apply the result to local state. The thermostat's next
        `GET /config` then serves our merged local tree naturally.

        Side effects:
          * `store.apply_config` runs the pending-write replay path,
            so any HA-side mutations queued in `pending_writes`
            (within the grace window) are merged onto Carrier's tree.
          * After apply, we mark `config_dirty=True` so the next
            status-POST directive tells the thermostat to pull the
            fresh tree.

        Returns True iff Carrier returned a 200 with a parseable body
        we successfully applied. Failures are logged but not
        propagated — HA's view of state stays whatever it was; the
        thermostat keeps running on its existing tree.
        """
        if not self._enabled or self._client is None:
            return False
        # Re-use the same relay machinery (circuit breaker, auth
        # capture, capture-traffic insertion all consistent).
        relayed = await self.relay(
            "GET", f"/systems/{serial}/config",
            local_changes_pending=False,
        )
        if relayed is None or relayed.status_code != 200 or not relayed.body:
            return False
        # Local imports to avoid circular: parser/state_store both
        # import this module's name.
        from .parser import parse_system_config_with_tree
        try:
            tree, config = parse_system_config_with_tree(relayed.body)
        except Exception as e:
            logger.warning(
                "pull_and_apply_config: parse failed for serial=%s: %s",
                serial, e,
            )
            return False
        await store.apply_config(serial, config, tree)
        # Force dirty so the next status-POST directive signals
        # configHasChanges=true and the thermostat fetches the new
        # tree. apply_config only sets dirty automatically when its
        # replay layer mutates the tree (i.e. there were pending HA
        # writes); on a clean Carrier-app-set apply with no pending
        # writes, dirty would otherwise stay False and the device
        # wouldn't pick up the change until something else flipped it.
        await store.mark_config_dirty()
        logger.info(
            "pull_and_apply_config: applied Carrier tree to local "
            "store (serial=%s, %d B)", serial, len(relayed.body),
        )
        return True

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
        southbound can decide whether to fire `pull_and_apply_config`."""
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


def _action_key(method: str, path: str, query: str | None) -> str:
    """Compose a stable identifier for a Carrier-bound request.

    Kept after the alpha.48 cache deletion because tests still use it
    as a stable label and a future capture-correlation column would
    need the same shape. Path-only keying mirrored upstream Perl
    `$nk = $url->path->to_string` (with a `-` separator instead of
    `/`).
    """
    base = f"{method.upper()} {path}"
    if query:
        base = f"{base}?{query}"
    return base
