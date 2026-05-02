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
    """Polls the Python proxy's /v1/* endpoints."""

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
                activities_results = await asyncio.gather(*activities_tasks)
                schedule_results = await asyncio.gather(*schedule_tasks)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Infinitude: {err}") from err

        zone_aux: dict[str, dict] = {
            zid: {
                "activities": activities_results[i],
                "schedule": schedule_results[i],
            }
            for i, zid in enumerate(zone_ids)
        }
        return self._shape(state, healthz, zone_aux)

    async def _get_obj(self, path: str) -> dict:
        resp = await self._session.get(f"{self.host}{path}")
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
            "carrier_ok": carrier_status == "healthy",
            "carrier_status": carrier_status,
            "thermostat_status": thermostat_status,
            "stale": thermostat_status != "healthy",
            "lastUpdated": state.get("lastUpdated"),
        }

    # ── Optimistic overlay ────────────────────────────────────────────────

    def _set_optimistic(self, key: str, patch: dict) -> None:
        """Stash an expected partial zone/system shape and immediately
        replay it through the coordinator's data so listeners see the
        new state on write completion rather than after the next poll
        (write→thermostat pull→addon state-reflect is ~30 s worst case).

        `patch` is shallow-merged onto the live zone/system dict. Any
        field can be overlaid; common patches include `hold`,
        `heatSetpoint`, `coolSetpoint`, `currentActivity`. The overlay
        is dropped on first poll where every patched field has converged
        to the optimistic value, or after `_OPTIMISTIC_TTL`.

        Uses `async_set_updated_data` (substitute + notify atomically)
        instead of in-place mutation — HA's CoordinatorEntity diff path
        relies on a fresh data ref.
        """
        existing = self._optimistic.get(key, {}).get("patch", {})
        merged = {**existing, **patch}
        self._optimistic[key] = {
            "patch": merged,
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
