"""Data coordinator for Infinitude Direct.

Talks to the Python/FastAPI proxy's `/v1/*` API (typed JSON). The state
shape returned here mirrors `/v1/state` verbatim (system + zones), with
per-zone `activities` and `schedule` folded in and `host`/`carrier_ok`/
`stale` synthesized from `/v1/healthz`.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

_DAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

# Optimistic-hold lifetime: write → thermostat pull → addon state reflect
# can take a full config-poll cycle (~30 s). Overlay expected state until
# the real state catches up, with a generous upper bound so a failed
# round-trip doesn't leave the UI stuck on a phantom hold.
_OPTIMISTIC_TTL = timedelta(seconds=90)


class InfinitudeDataCoordinator(DataUpdateCoordinator):
    """Polls the Python proxy's /v1/* endpoints AND consumes its SSE
    stream for near-real-time push updates.

    Two paths feed `self.data`:

      * Periodic poll (`update_interval`) — heartbeat / safety net for
        the case where SSE silently drops or events are missed. Cadence
        is bumped from 30 s (pre-SSE) to 60 s now that SSE handles
        live updates.
      * SSE consumer (`_sse_loop`) — long-lived task subscribed to
        `/v1/events`. Each event triggers a coordinator refresh
        (debounced), so state changes from the thermostat side
        (current temp, panel-set hold, fault notifications, etc.)
        appear in HA within ~1 s instead of waiting for the next
        poll. Reconnects with exponential backoff and the
        `Last-Event-ID` header so missed events get replayed from
        the addon's ring buffer.
    """

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.host = host.rstrip("/")
        self._session = async_get_clientsession(hass)
        self.api_lock = asyncio.Lock()
        # zone_id → {"hold": {...}, "expires": datetime}. "system" for whole-house.
        self._optimistic: dict[str, dict] = {}
        # SSE state — task lifetime tracked here so we can cancel on
        # unload. `_sse_connected` flips on each connect/disconnect and
        # is exposed to the system-info sensor so the UI can show a
        # tri-state "live updates" indicator.
        self._sse_task: asyncio.Task | None = None
        self._sse_last_event_id: str | None = None
        self._sse_connected: bool = False

    @property
    def sse_connected(self) -> bool:
        return self._sse_connected

    def start_sse(self) -> None:
        """Launch the SSE consumer as a background task. Idempotent —
        called from __init__.py after the first refresh succeeds.
        Cancels itself on coordinator shutdown via async_shutdown."""
        if self._sse_task is not None and not self._sse_task.done():
            return
        self._sse_task = self.hass.async_create_background_task(
            self._sse_loop(), name=f"{DOMAIN}_sse_consumer",
        )

    async def async_shutdown(self) -> None:
        if self._sse_task is not None:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except (asyncio.CancelledError, Exception):
                pass
            self._sse_task = None
        self._sse_connected = False
        await super().async_shutdown()

    async def _async_update_data(self) -> dict:
        try:
            async with asyncio.timeout(15):
                state, healthz = await asyncio.gather(
                    self._get_obj("/v1/state"),
                    self._get_obj("/v1/healthz"),
                )
                zone_ids = [
                    z["id"] for z in state.get("zones", []) if z.get("enabled", True)
                ]
                activities_tasks = [
                    self._get_list(f"/v1/zones/{zid}/activities") for zid in zone_ids
                ]
                schedule_tasks = [
                    self._get_obj(f"/v1/zones/{zid}/schedule") for zid in zone_ids
                ]
                # Optional aux endpoints — these 404 on a fresh proxy
                # install until the thermostat sends the corresponding
                # POST (energy ~daily, equipment_events on demand,
                # odu/idu_status every few minutes when running).
                # `_get_obj_optional` returns None on 404 so the
                # coordinator doesn't fail just because an endpoint
                # hasn't been seeded yet.
                aux_tasks = [
                    self._get_obj_optional("/v1/system/energy"),
                    self._get_obj_optional("/v1/system/odu_status"),
                    self._get_obj_optional("/v1/system/idu_status"),
                    self._get_obj_optional("/v1/system/events"),
                ]
                activities_results = await asyncio.gather(*activities_tasks)
                schedule_results = await asyncio.gather(*schedule_tasks)
                energy, odu_status, idu_status, events = await asyncio.gather(
                    *aux_tasks
                )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Infinitude: {err}") from err

        zone_aux: dict[str, dict] = {
            zid: {
                "activities": activities_results[i],
                "schedule": schedule_results[i],
            }
            for i, zid in enumerate(zone_ids)
        }
        shaped = self._shape(state, healthz, zone_aux)
        # Optional snapshots — sensors check for None and report
        # unavailable when the underlying endpoint hasn't been seeded.
        shaped["energy"] = energy
        shaped["odu_status"] = odu_status
        shaped["idu_status"] = idu_status
        shaped["events"] = events
        return shaped

    async def _get_obj(self, path: str) -> dict:
        resp = await self._session.get(f"{self.host}{path}")
        resp.raise_for_status()
        data = await resp.json(content_type=None)
        if not isinstance(data, dict):
            raise UpdateFailed(f"Expected JSON object at {path}, got {type(data).__name__}")
        return data

    async def _get_obj_optional(self, path: str) -> dict | None:
        """Same as `_get_obj` but returns None on 404 instead of
        raising. Used for `/v1/system/{energy,odu_status,idu_status,events}`
        which 404 until the thermostat first POSTs the corresponding
        sub-resource."""
        resp = await self._session.get(f"{self.host}{path}")
        if resp.status == 404:
            return None
        resp.raise_for_status()
        data = await resp.json(content_type=None)
        if not isinstance(data, dict):
            raise UpdateFailed(f"Expected JSON object at {path}, got {type(data).__name__}")
        return data

    async def _get_list(self, path: str) -> list:
        resp = await self._session.get(f"{self.host}{path}")
        resp.raise_for_status()
        data = await resp.json(content_type=None)
        if not isinstance(data, list):
            raise UpdateFailed(f"Expected JSON array at {path}, got {type(data).__name__}")
        return data

    def _shape(self, state: dict, healthz: dict, zone_aux: dict) -> dict:
        components = healthz.get("components", {})
        thermostat_status = components.get("thermostat", {}).get("status", "unreachable")
        carrier_status = components.get("carrierCloud", {}).get("status", "disabled")
        # Tri-state for the HVAC card's "Carrier cloud:" indicator dot:
        #   healthy             → True  (green)
        #   degraded/unreachable → False (red — actual problem)
        #   unknown/disabled    → None  (grey — neutral, not "broken")
        # The card's status-card.js / hvac-card.js read this off the
        # system_info sensor attribute and switch class accordingly.
        if carrier_status == "healthy":
            carrier_ok: bool | None = True
        elif carrier_status in ("degraded", "unreachable"):
            carrier_ok = False
        else:
            carrier_ok = None

        system = dict(state.get("system", {}))
        self._apply_optimistic_system(system)

        zones: list[dict] = []
        for z in state.get("zones", []):
            if not z.get("enabled", True):
                continue
            aux = zone_aux.get(z["id"], {})
            activities_map = {
                a["id"]: {"heat": a["heat"], "cool": a["cool"], "fan": a["fan"]}
                for a in aux.get("activities", [])
            }
            schedule_map = {
                d["day"]: d.get("periods", [])
                for d in aux.get("schedule", {}).get("days", [])
            }
            zone = {**z, "activities": activities_map, "schedule": schedule_map}
            self._apply_optimistic_zone(zone)
            zones.append(zone)

        return {
            "system": system,
            "zones": zones,
            "host": self.host,
            "carrier_ok": carrier_ok,
            "carrier_status": carrier_status,
            "thermostat_status": thermostat_status,
            "stale": thermostat_status != "healthy",
            "lastUpdated": state.get("lastUpdated"),
            # Live-event-stream connection state. The system_info
            # sensor reads this so the HVAC card can show a tri-state
            # "Infinitude: connected" indicator (green = polling +
            # SSE both healthy; yellow = polling alive, SSE
            # disconnected; red = sensor unavailable).
            "sse_connected": self._sse_connected,
        }

    # ── Optimistic overlay ────────────────────────────────────────────────

    def _set_optimistic(self, key: str, patch: dict) -> None:
        """Stash an expected partial zone/system shape and immediately
        replay it through the coordinator's data so listeners see the
        new state on write completion rather than after the next poll
        (write→thermostat pull→addon state-reflect is ~30 s worst case).

        Each call **replaces** the prior optimistic patch for `key`,
        not merges. Replace semantics matter for cancel flows: after
        `set_hold("away")` the patch carries `currentActivity:"away"`,
        and the follow-up `cancel_hold` would otherwise leave that
        currentActivity sticking around for 90 s while the
        actually-active scheduled activity is shown as `preset_mode`.
        Each coordinator write describes the current intent in full,
        not as a delta on the prior intent.

        `patch` is shallow-merged onto the live zone/system dict in
        `self.data` — that's just the synchronous UI flip. Any field
        can be overlaid; common patches include `hold`, `heatSetpoint`,
        `coolSetpoint`, `currentActivity`. The overlay is dropped on
        the first poll where every patched field has converged to the
        optimistic value, or after `_OPTIMISTIC_TTL`.

        Uses `async_set_updated_data` (substitute + notify atomically)
        instead of in-place mutation — HA's CoordinatorEntity diff path
        relies on a fresh data ref.
        """
        self._optimistic[key] = {
            "patch": dict(patch),
            "expires": dt_util.utcnow() + _OPTIMISTIC_TTL,
        }
        if not isinstance(self.data, dict):
            return
        new_data = dict(self.data)
        if key == "system":
            new_data["system"] = {**(new_data.get("system") or {}), **patch}
        else:
            new_data["zones"] = [
                {**z, **patch} if z.get("id") == key else z
                for z in new_data.get("zones", [])
            ]
        self.async_set_updated_data(new_data)

    def _apply_optimistic_zone(self, zone: dict) -> None:
        patch = self._pop_expired(zone["id"])
        if patch is None:
            return
        if _patch_converged(zone, patch):
            self._optimistic.pop(zone["id"], None)
            return
        zone.update(patch)

    def _apply_optimistic_system(self, system: dict) -> None:
        patch = self._pop_expired("system")
        if patch is None:
            return
        if _patch_converged(system, patch):
            self._optimistic.pop("system", None)
            return
        system.update(patch)

    def _pop_expired(self, key: str) -> dict | None:
        """Return the active optimistic patch, or None if expired/absent.

        Misleading name (kept for diff stability) — returns the patch
        when it's still valid; pops + returns None when the TTL has
        elapsed.
        """
        entry = self._optimistic.get(key)
        if entry is None:
            return None
        if dt_util.utcnow() >= entry["expires"]:
            self._optimistic.pop(key, None)
            return None
        return entry["patch"]

    # ── Write methods ──────────────────────────────────────────────────────

    async def async_set_mode(self, mode: str) -> None:
        await self._patch("/v1/system", {"mode": mode})
        # Closes the ~100 ms gap between the PATCH return and the next
        # coordinator refresh — without this the climate entity reads
        # the pre-write `system.mode` from `self.data` until the refresh
        # comes back, and HA's frontend optimistic clears + snaps.
        self._set_optimistic("system", {"mode": mode})

    async def async_set_hold(
        self, zone_id: str, activity: str, until: str | None = None
    ) -> None:
        body = self._build_hold_body(activity, until)
        await self._put(f"/v1/zones/{zone_id}/hold", body)
        self._set_optimistic(zone_id, {
            "hold": {
                "active": True,
                "activity": activity,
                "until": body.get("until"),
            },
            "currentActivity": activity,
        })

    async def async_cancel_hold(self, zone_id: str) -> None:
        await self._delete(f"/v1/zones/{zone_id}/hold")
        self._set_optimistic(zone_id, {
            "hold": {"active": False, "activity": None, "until": None},
        })

    async def async_set_activity_temps(
        self, zone_id: str, activity: str, htsp: int, clsp: int
    ) -> None:
        await self._patch(
            f"/v1/zones/{zone_id}/activities/{activity}",
            {"heat": int(htsp), "cool": int(clsp)},
        )
        # Setpoints are surfaced on the zone only when the held
        # activity is the one we just edited. Stash optimistic so the
        # climate entity flips its target_temp immediately rather than
        # snapping back to telemetry's pre-write value while the
        # thermostat catches up. async_set_hold's optimistic for the
        # hold-activity itself is set separately by the caller.
        self._set_optimistic(zone_id, {
            "heatSetpoint": int(htsp),
            "coolSetpoint": int(clsp),
        })

    async def async_set_activity_fan(
        self, zone_id: str, activity: str, fan: str
    ) -> None:
        await self._patch(
            f"/v1/zones/{zone_id}/activities/{activity}", {"fan": fan}
        )
        # Same reasoning as async_set_activity_temps — the zone surface
        # only displays the held activity's fan, so we only stash the
        # optimistic when the activity we just patched is the one that
        # would be visible. Avoids flashing a stale fan value if the
        # user edits a non-active activity.
        zone = next(
            (z for z in self.data.get("zones", []) if z.get("id") == zone_id),
            None,
        ) if isinstance(self.data, dict) else None
        if zone is None:
            return
        hold = zone.get("hold") or {}
        held_activity = hold.get("activity") if hold.get("active") else None
        active_activity = held_activity or zone.get("currentActivity")
        if active_activity == activity:
            self._set_optimistic(zone_id, {"fan": fan})

    async def async_set_whole_house_hold(
        self, activity: str, until: str | None = None
    ) -> None:
        body = self._build_hold_body(activity, until)
        await self._put("/v1/system/hold", body)
        self._set_optimistic("system", {
            "hold": {
                "active": True,
                "activity": activity,
                "until": body.get("until"),
            },
        })

    async def async_cancel_whole_house_hold(self) -> None:
        await self._delete("/v1/system/hold")
        self._set_optimistic("system", {
            "hold": {"active": False, "activity": None, "until": None},
        })

    async def async_save_schedule(self, zone_id: str, program: list) -> None:
        """Write a zone's weekly schedule.

        Accepts the legacy HVAC card shape (lowercase day ids, string
        period ids, `enabled: "on"|"off"`); translates to the typed
        `PUT /v1/zones/{id}/schedule` body. Missing days are filled from
        the current schedule so the card's partial-update UX still works.
        """
        async with self.api_lock:
            current = await self._get_obj(f"/v1/zones/{zone_id}/schedule")
            day_map: dict[str, dict] = {
                d["day"]: d for d in current.get("days", [])
            }

            for d in program:
                raw = (d.get("id") or d.get("day") or "").strip()
                if not raw:
                    continue
                day_name = raw.capitalize()
                if day_name not in day_map:
                    continue
                periods_in = d.get("period") or d.get("periods") or []
                day_map[day_name]["periods"] = [
                    _normalize_period(p) for p in periods_in
                ]

            body = {"days": [day_map[d] for d in _DAY_ORDER if d in day_map]}
            resp = await self._session.put(
                f"{self.host}/v1/zones/{zone_id}/schedule", json=body
            )
            resp.raise_for_status()

    # ── HTTP helpers ───────────────────────────────────────────────────────

    def _build_hold_body(self, activity: str, until: str | None) -> dict:
        """Build a hold-request body. `until` semantics:
          * None or "forever" → indefinite (omit `until`).
          * "auto"            → 2 h from now, as HH:MM in HA's local tz.
          * "HH:MM"           → passed through verbatim.

        The addon treats `until` as a bare wall-clock time (HH:MM) that
        the thermostat will evaluate against its own local clock — no
        timezone round-trip involved, which avoided a UTC-vs-local drift
        when the addon container and the HA host were in different
        zones.
        """
        body: dict = {"activity": activity}
        if until is None or until == "forever":
            return body
        if until == "auto":
            body["until"] = _hhmm_from_now(2)
            return body
        if _HHMM_RE.match(until.strip()):
            body["until"] = until.strip()
            return body
        _LOGGER.warning(
            "Unparseable hold 'until' value %r; falling back to 2h hold", until
        )
        body["until"] = _hhmm_from_now(2)
        return body

    async def _patch(self, path: str, body: dict) -> None:
        resp = await self._session.patch(f"{self.host}{path}", json=body)
        resp.raise_for_status()

    async def _put(self, path: str, body: dict) -> None:
        resp = await self._session.put(f"{self.host}{path}", json=body)
        resp.raise_for_status()

    async def _delete(self, path: str) -> None:
        resp = await self._session.delete(f"{self.host}{path}")
        resp.raise_for_status()

    # ── SSE consumer ───────────────────────────────────────────────────────

    async def _sse_loop(self) -> None:
        """Long-lived task: maintain an SSE connection to /v1/events.

        Backoff is exponential with a 60 s ceiling. Resumes via the
        addon's `Last-Event-ID` ring-buffer so events emitted while we
        were disconnected get replayed (or, if our id is too old, the
        addon re-seeds with a fresh `state.snapshot`).

        Polling-vs-SSE coordination lives in `_sse_consume_once` /
        `_on_sse_disconnect` — when SSE is up, scheduled polling is
        disabled (the keepalive ping is the heartbeat); when SSE
        drops, polling resumes immediately.
        """
        backoff = 1.0
        while True:
            try:
                await self._sse_consume_once()
                # Clean EOF (server closed cleanly) — reset backoff
                # so the next reconnect is fast.
                backoff = 1.0
                _LOGGER.info("SSE: stream ended cleanly; reconnecting")
            except asyncio.CancelledError:
                # Coordinator unload — leave _sse_connected/polling
                # state alone; async_shutdown handles teardown.
                raise
            except Exception as err:
                _LOGGER.warning(
                    "SSE: %s — reconnecting in %.1fs", err, backoff,
                )
                # Centralised disconnect bookkeeping — flips the dot
                # to yellow AND re-enables polling. Without this the
                # coordinator would have `update_interval=None` from
                # the prior connect and never refresh during the
                # reconnect window. Async so we can await the inner
                # `async_request_refresh` (without the await, the
                # coroutine is GC'd unfinished and HA logs a warning).
                await self._on_sse_disconnect()
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise
            backoff = min(backoff * 2.0, 60.0)

    async def _sse_consume_once(self) -> None:
        """One full connect → consume → disconnect cycle. Returns
        normally on EOF; raises on network or HTTP errors so the outer
        loop can apply backoff.

        Side effect: toggles `update_interval` to disable scheduled
        polling while SSE is connected (the addon's 15 s keepalive
        ping is the heartbeat — polling would be redundant). On
        disconnect we resume the 60 s heartbeat poll AND fire an
        immediate refresh so the user sees state without waiting a
        full poll cycle.
        """
        headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}
        if self._sse_last_event_id:
            headers["Last-Event-ID"] = self._sse_last_event_id

        # `sock_read` timeout = 60 s catches a half-open TCP without
        # killing the long-lived stream itself. The addon emits a
        # keepalive comment every 15 s, so a 60 s read-silence means
        # the connection is genuinely dead.
        timeout = aiohttp.ClientTimeout(total=None, sock_read=60)
        async with self._session.get(
            f"{self.host}/v1/events", headers=headers, timeout=timeout,
        ) as resp:
            resp.raise_for_status()
            self._sse_connected = True
            # Disable scheduled polling — the SSE keepalive does the
            # heartbeat job, and `state.update` events fire on every
            # thermostat status post (~30 s) so we get fresher
            # updates than the 60 s poll would give us anyway.
            self.update_interval = None
            _LOGGER.info(
                "SSE: connected (resume id=%s); pause poll heartbeat",
                self._sse_last_event_id or "none",
            )
            # Push a refresh so the UI's "SSE connected" indicator
            # flips green immediately rather than waiting for the
            # next poll-driven `async_set_updated_data`.
            self.async_update_listeners()
            await self._parse_sse_stream(resp)
        # Stream ended cleanly (server closed) — fall through to
        # disconnect handling in the finally-style block below.
        await self._on_sse_disconnect()

    async def _on_sse_disconnect(self) -> None:
        """Centralised disconnect bookkeeping — flip the indicator
        and re-enable polling so the user keeps getting updates while
        the SSE consumer's outer loop reconnects with backoff.

        Async because `async_request_refresh()` is a coroutine — early
        in alpha.30 this was sync and the bare call left an unawaited-
        coroutine warning behind on every reconnect cycle.
        """
        if not self._sse_connected:
            return  # already disconnected; idempotent
        self._sse_connected = False
        # Re-arm the heartbeat poll (matches the const default — we
        # only switch it off, never permanently rebase). The next
        # tick fires after `update_interval` from now.
        self.update_interval = timedelta(seconds=SCAN_INTERVAL_SECONDS)
        _LOGGER.info("SSE: disconnected; resume %ds poll heartbeat", SCAN_INTERVAL_SECONDS)
        self.async_update_listeners()
        # Don't wait for the next interval — kick a refresh now so
        # the gap between SSE-stop and first-poll-arrival doesn't
        # show stale data.
        await self.async_request_refresh()

    async def _parse_sse_stream(self, resp) -> None:
        """SSE line-format parser per https://html.spec.whatwg.org/#server-sent-events.

        Fields we care about:
          * `id:` — monotonic event id; we save it for resume.
          * `event:` — event type (state.snapshot / state.update /
            hold.changed / health.changed). Default is `message`.
          * `data:` — JSON payload; multi-line allowed (concatenated
            with newlines).
          * lines starting with `:` — comments; addon emits them every
            15 s as keepalive, ignored here.

        Blank line terminates an event; we then dispatch.
        """
        event_id: str | None = None
        event_type: str = "message"
        data_lines: list[str] = []
        while True:
            raw = await resp.content.readline()
            if not raw:
                # Connection closed by server; outer loop reconnects.
                return
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                # Blank line: dispatch and reset.
                if data_lines:
                    if event_id is not None:
                        self._sse_last_event_id = event_id
                    await self._handle_sse_event(
                        event_type, "\n".join(data_lines),
                    )
                event_id = None
                event_type = "message"
                data_lines = []
                continue
            if line.startswith(":"):
                # Comment / keepalive — ignore.
                continue
            field, _, value = line.partition(":")
            if value.startswith(" "):
                value = value[1:]
            if field == "id":
                event_id = value
            elif field == "event":
                event_type = value
            elif field == "data":
                data_lines.append(value)
            # Other field names (`retry:`) ignored — we use our own
            # backoff schedule.

    async def _handle_sse_event(self, event_type: str, data: str) -> None:
        """Dispatch one parsed event.

        Strategy: every state-shaped event triggers a coordinator
        refresh. This is simpler than parsing each payload and
        applying surgical patches — `/v1/state` is small and
        `async_request_refresh()` is debounced so a flurry of events
        coalesces into one refresh. Trade-off: a few extra ms per
        event for one fewer code path that can drift from the
        addon's actual state shape.

        `notifications.received` triggers refresh too so the
        notifications ring buffer fetched via /v1/notifications is
        fresh by the time downstream entities read it. (alpha.31:
        notifications are now on the SSE stream — pre-31 they were
        REST-poll only and HA saw them up to a poll cycle late.)

        `health.changed` is published when mutation drift fires; not
        a state change for the user-facing UI, so we don't refresh on
        it.
        """
        # Per-event DEBUG log — quiet in normal operation (INFO on
        # connect/disconnect already records the lifecycle), turn on
        # `log_level: debug` to see live event flow when debugging
        # latency or "did this event arrive?" questions.
        _LOGGER.debug(
            "SSE event: %s id=%s data=%s",
            event_type, self._sse_last_event_id, data[:200],
        )
        if event_type in (
            "state.snapshot",
            "state.update",
            "hold.changed",
            "notifications.received",
        ):
            await self.async_request_refresh()


_HHMM_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _hhmm_from_now(hours: int) -> str:
    """Return HH:MM `hours` from now in HA's configured timezone.

    The thermostat's <otmr> is a bare wall-clock time compared against
    its own local clock, so we hand it HH:MM matching the user's
    actual local time (via HA's tz config), not the addon container's
    process tz.
    """
    target = dt_util.now() + timedelta(hours=hours)
    return f"{target.hour:02d}:{target.minute:02d}"


def _patch_converged(real: dict, patch: dict) -> bool:
    """True when every field in `patch` has caught up in `real`.

    Field-aware comparison — `hold` is compared loosely (active /
    activity / presence-of-until) because the server quarter-hour-snaps
    HH:MM and we don't want to fight that. Other fields are compared
    by value; falsy variants normalize to None first so absent vs.
    null vs. empty string don't keep the overlay sticky.
    """
    for k, want in patch.items():
        got = real.get(k)
        if k == "hold":
            if not _hold_matches(got or {}, want or {}):
                return False
        else:
            if (got or None) != (want or None):
                return False
    return True


def _hold_matches(real: dict, expected: dict) -> bool:
    if bool(real.get("active")) != bool(expected.get("active")):
        return False
    if (real.get("activity") or None) != (expected.get("activity") or None):
        return False
    if bool(real.get("until")) != bool(expected.get("until")):
        return False
    return True


def _normalize_period(p: dict) -> dict:
    pid = p["id"]
    if isinstance(pid, str):
        pid = int(pid)
    enabled = p.get("enabled")
    if isinstance(enabled, bool):
        pass
    elif isinstance(enabled, str):
        enabled = enabled.lower() in ("on", "true", "1", "yes")
    elif isinstance(enabled, int):
        enabled = bool(enabled)
    else:
        enabled = False
    return {
        "id": pid,
        "activity": p["activity"],
        "time": p["time"],
        "enabled": enabled,
    }
