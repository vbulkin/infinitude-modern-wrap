"""Data coordinator for Infinitude Direct."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class InfinitudeDataCoordinator(DataUpdateCoordinator):
    """Polls Infinitude's systems.json and status.json endpoints."""

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
        self._last_local_time: str | None = None
        self._stale_count: int = 0

    async def _async_update_data(self) -> dict:
        try:
            async with asyncio.timeout(15):
                systems_resp = await self._session.get(f"{self.host}/systems.json")
                systems_resp.raise_for_status()
                systems = await systems_resp.json(content_type=None)

                status_resp = await self._session.get(f"{self.host}/status.json")
                status_resp.raise_for_status()
                status = await status_resp.json(content_type=None)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Infinitude: {err}") from err

        parsed = self._parse(systems, status)
        self._update_staleness(parsed.get("local_time"))
        parsed["stale"] = self._stale_count >= 2
        return parsed

    def _update_staleness(self, local_time: str | None) -> None:
        if not local_time:
            return
        if self._last_local_time and local_time == self._last_local_time:
            self._stale_count += 1
        else:
            self._stale_count = 0
        self._last_local_time = local_time

    def _parse(self, systems: dict, status: dict) -> dict:
        cfg = systems["system"][0]["config"][0]
        st = status["status"][0]

        mode = self._v(cfg.get("mode")) or "off"
        oat = self._v(st.get("oat"))

        cfg_zones = self._force_array(cfg["zones"][0]["zone"])
        status_zones = self._force_array(st["zones"][0]["zone"])

        zone_map = {}
        for cz in cfg_zones:
            zone_map[cz["id"]] = cz

        zones = []
        for sz in status_zones:
            if self._v(sz.get("enabled")) != "on":
                continue

            cz = zone_map.get(sz["id"], {})

            activities = {}
            if "activities" in cz and cz["activities"]:
                for act in self._force_array(
                    cz["activities"][0].get("activity", [])
                ):
                    act_id = act.get("id")
                    if act_id:
                        activities[act_id] = {
                            "htsp": self._v(act.get("htsp")),
                            "clsp": self._v(act.get("clsp")),
                            "fan": self._v(act.get("fan")),
                        }

            zones.append(
                {
                    "id": sz["id"],
                    "name": self._v(sz.get("name")) or f"Zone {sz['id']}",
                    "temp": self._v(sz.get("rt")),
                    "rh": self._v(sz.get("rh")),
                    "htsp": self._v(sz.get("htsp")),
                    "clsp": self._v(sz.get("clsp")),
                    "conditioning": self._v(sz.get("zoneconditioning")) or "idle",
                    "currentActivity": self._v(sz.get("currentActivity")) or "home",
                    "hold": self._v(cz.get("hold")) == "on",
                    "holdActivity": self._v(cz.get("holdActivity")),
                    "fan": self._v(sz.get("fan")),
                    "damper": self._v(sz.get("damperposition")),
                    "activities": activities,
                }
            )

        humid = self._v(st.get("humid")) or "off"
        local_time = self._v(st.get("localTime"))
        op_status = self._v(st.get("oprstsmsg")) or ""

        # Parse schedule (program) data per zone
        schedule = {}
        for sz in zones:
            cz = zone_map.get(sz["id"], {})
            zone_sched = {}
            if "program" in cz and cz["program"]:
                days = self._force_array(cz["program"][0].get("day", []))
                for day in days:
                    day_id = day.get("id")
                    if not day_id:
                        continue
                    periods = []
                    for p in self._force_array(day.get("period", [])):
                        periods.append({
                            "id": self._v(p.get("id")) or p.get("id"),
                            "activity": self._v(p.get("activity")) or "home",
                            "time": self._v(p.get("time")) or "00:00",
                            "enabled": self._v(p.get("enabled")) == "on",
                        })
                    zone_sched[day_id] = periods
            schedule[sz["id"]] = zone_sched

        return {
            "mode": mode,
            "oat": oat,
            "op_status": op_status,
            "humid": humid,
            "local_time": local_time,
            "host": self.host,
            "zones": zones,
            "schedule": schedule,
            "whole_house_hold": self._parse_whole_house(cfg),
        }

    def _parse_whole_house(self, cfg: dict) -> dict:
        wh = cfg.get("wholeHouse")
        if not wh:
            return {"hold": False, "holdActivity": None, "otmr": None}
        wh = wh[0] if isinstance(wh, list) else wh
        return {
            "hold": self._v(wh.get("hold")) == "on",
            "holdActivity": self._v(wh.get("holdActivity")),
            "otmr": self._v(wh.get("otmr")),
        }

    @staticmethod
    def _v(x):
        """Unwrap Infinitude's single-element array values. [{}] → None."""
        if not isinstance(x, list) or len(x) == 0:
            return None
        val = x[0]
        if val is None:
            return None
        if isinstance(val, dict) and len(val) == 0:
            return None
        return val

    @staticmethod
    def _force_array(x):
        if isinstance(x, list):
            return x
        return [x] if x else []

    # ── Write methods ──────────────────────────────────────────────────────

    @staticmethod
    def otmr_from_now(hours: int = 2) -> str:
        """Return an HH:MM string *hours* from now, rounded to 15 min."""
        from datetime import datetime, timedelta

        target = datetime.now() + timedelta(hours=hours)
        minutes = round(target.minute / 15) * 15
        if minutes == 60:
            target = target.replace(minute=0) + timedelta(hours=1)
        else:
            target = target.replace(minute=minutes, second=0, microsecond=0)
        return target.strftime("%H:%M")

    async def async_set_mode(self, mode: str) -> None:
        await self._session.put(
            f"{self.host}/api/config",
            params={"mode": mode, "set_changes": "true"},
        )

    async def async_set_hold(
        self, zone_id: str, activity: str, until: str | None = None
    ) -> None:
        if until is None:
            until = self.otmr_from_now(2)
        await self._session.put(
            f"{self.host}/api/{zone_id}/hold",
            params={"activity": activity, "until": until},
        )

    async def async_cancel_hold(self, zone_id: str) -> None:
        await self._session.put(
            f"{self.host}/api/{zone_id}/hold",
            params={"hold": "off"},
        )

    async def async_set_activity_temps(
        self, zone_id: str, activity: str, htsp: int, clsp: int
    ) -> None:
        await self._session.put(
            f"{self.host}/api/{zone_id}/activity/{activity}",
            params={"htsp": str(htsp), "clsp": str(clsp)},
        )

    async def async_set_whole_house_hold(
        self, activity: str, otmr: str | None = None
    ) -> None:
        params = {
            "hold": "on",
            "holdActivity": activity,
            "set_changes": "true",
        }
        if otmr:
            params["otmr"] = otmr
        await self._session.put(
            f"{self.host}/api/config/wholeHouse",
            params=params,
        )

    async def async_cancel_whole_house_hold(self) -> None:
        await self._session.put(
            f"{self.host}/api/config/wholeHouse",
            params={"hold": "off", "set_changes": "true"},
        )

    async def async_save_schedule(self, zone_id: str, program: list) -> None:
        """Save full schedule for a zone. program = list of {id, period[]}."""
        await self._session.put(
            f"{self.host}/api/config/zones/zone/{zone_id}/program",
            json={"day": program},
        )

    async def async_set_activity_fan(
        self, zone_id: str, activity: str, fan: str
    ) -> None:
        await self._session.put(
            f"{self.host}/api/{zone_id}/activity/{activity}",
            params={"fan": fan},
        )
