"""Data coordinator for Infinitude Direct.

Talks to the Python/FastAPI proxy's `/v1/*` API (typed JSON). The state
shape returned here mirrors `/v1/state` verbatim (system + zones), with
per-zone `activities` and `schedule` folded in and `host`/`carrier_ok`/
`stale` synthesized from `/v1/healthz`.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

_DAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


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
            zones.append({**z, "activities": activities_map, "schedule": schedule_map})

        return {
            "system": state.get("system", {}),
            "zones": zones,
            "host": self.host,
            "carrier_ok": carrier_status == "healthy",
            "carrier_status": carrier_status,
            "thermostat_status": thermostat_status,
            "stale": thermostat_status != "healthy",
            "lastUpdated": state.get("lastUpdated"),
        }

    # ── Write methods ──────────────────────────────────────────────────────

    @staticmethod
    def isotime_from_now(hours: int = 2) -> str:
        """Return an ISO-8601 UTC timestamp `hours` from now (Z-suffixed)."""
        target = datetime.now(timezone.utc) + timedelta(hours=hours)
        return target.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def async_set_mode(self, mode: str) -> None:
        await self._patch("/v1/system", {"mode": mode})

    async def async_set_hold(
        self, zone_id: str, activity: str, until: str | None = None
    ) -> None:
        body = self._build_hold_body(activity, until)
        await self._put(f"/v1/zones/{zone_id}/hold", body)

    async def async_cancel_hold(self, zone_id: str) -> None:
        await self._delete(f"/v1/zones/{zone_id}/hold")

    async def async_set_activity_temps(
        self, zone_id: str, activity: str, htsp: int, clsp: int
    ) -> None:
        await self._patch(
            f"/v1/zones/{zone_id}/activities/{activity}",
            {"heat": int(htsp), "cool": int(clsp)},
        )

    async def async_set_activity_fan(
        self, zone_id: str, activity: str, fan: str
    ) -> None:
        await self._patch(
            f"/v1/zones/{zone_id}/activities/{activity}", {"fan": fan}
        )

    async def async_set_whole_house_hold(
        self, activity: str, until: str | None = None
    ) -> None:
        body = self._build_hold_body(activity, until)
        await self._put("/v1/system/hold", body)

    async def async_cancel_whole_house_hold(self) -> None:
        await self._delete("/v1/system/hold")

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

            body = {
                "zoneId": zone_id,
                "days": [day_map[d] for d in _DAY_ORDER if d in day_map],
            }
            resp = await self._session.put(
                f"{self.host}/v1/zones/{zone_id}/schedule", json=body
            )
            resp.raise_for_status()

    # ── HTTP helpers ───────────────────────────────────────────────────────

    def _build_hold_body(self, activity: str, until: str | None) -> dict:
        """Build a hold-request body. `until` semantics:
          * None or "forever" → indefinite (omit `until` — spec allows).
          * "auto"            → 2 h from now, ISO UTC.
          * ISO string        → used as-is.
          * "HH:MM"           → next local occurrence of that wall-clock
                                time, converted to ISO UTC. The backend
                                re-projects it back to HH:MM on the wire,
                                so the thermostat still evaluates it
                                against its own local clock.
        """
        body: dict = {"activity": activity}
        if until is None or until == "forever":
            return body
        if until == "auto":
            body["until"] = self.isotime_from_now(2)
            return body
        if "T" in until and until.endswith("Z"):
            body["until"] = until
            return body
        iso = _wall_time_to_iso_utc(until)
        if iso is None:
            _LOGGER.warning(
                "Unparseable hold 'until' value %r; falling back to 2h hold", until
            )
            body["until"] = self.isotime_from_now(2)
        else:
            body["until"] = iso
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


def _wall_time_to_iso_utc(hhmm: str) -> str | None:
    """Parse `HH:MM` as the next local occurrence of that wall-clock time
    and return it as an ISO-8601 UTC timestamp (Z-suffixed).

    Returns None if the input is not a valid HH:MM string.
    """
    m = _HHMM_RE.match(hhmm.strip())
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    now_local = dt_util.now()
    target = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now_local:
        target += timedelta(days=1)
    return dt_util.as_utc(target).strftime("%Y-%m-%dT%H:%M:%SZ")


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
