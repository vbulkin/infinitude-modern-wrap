"""Data coordinator for Infinitude Direct."""

import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

_CARRIER_OK_INTERVAL = 300  # 5 min when ok
_CARRIER_ERR_INTERVAL = 120  # 2 min when error


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
        self._carrier_ok: bool | None = None
        self._carrier_last_check: float = 0

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
        await self._check_carrier()
        parsed["carrier_ok"] = self._carrier_ok
        return parsed

    def _update_staleness(self, local_time: str | None) -> None:
        if not local_time:
            return
        if self._last_local_time and local_time == self._last_local_time:
            self._stale_count += 1
        else:
            self._stale_count = 0
        self._last_local_time = local_time

    async def _check_carrier(self) -> None:
        """Periodically check /Alive to see if Carrier cloud is reachable."""
        now = time.monotonic()
        interval = _CARRIER_OK_INTERVAL if self._carrier_ok else _CARRIER_ERR_INTERVAL
        if now - self._carrier_last_check < interval:
            return
        self._carrier_last_check = now
        try:
            async with asyncio.timeout(10):
                resp = await self._session.get(f"{self.host}/Alive")
                text = await resp.text()
                self._carrier_ok = resp.ok and "alive" in text.lower()
        except Exception:
            self._carrier_ok = False

    def _parse(self, systems: dict, status: dict) -> dict:
        try:
            cfg = systems["system"][0]["config"][0]
        except (KeyError, IndexError, TypeError) as err:
            raise UpdateFailed(f"Invalid systems.json structure: {err}") from err
        try:
            st = status["status"][0]
        except (KeyError, IndexError, TypeError) as err:
            raise UpdateFailed(f"Invalid status.json structure: {err}") from err

        mode = self._v(cfg.get("mode")) or "off"
        oat = self._v(st.get("oat"))

        cfg_zones = self._force_array(
            cfg.get("zones", [{}])[0].get("zone") if cfg.get("zones") else []
        )
        status_zones = self._force_array(
            st.get("zones", [{}])[0].get("zone") if st.get("zones") else []
        )

        zone_map = {}
        for cz in cfg_zones:
            zone_map[cz["id"]] = cz

        zones = []
        for sz in status_zones:
            if self._v(sz.get("enabled")) != "on":
                continue

            cz = zone_map.get(sz["id"], {})

            activities = {}
            cz_activities = cz.get("activities")
            if cz_activities:
                for act in self._force_array(
                    cz_activities[0].get("activity", []) if cz_activities else []
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
                    "otmr": self._v(cz.get("otmr")),
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
        wh = (wh[0] if wh else {}) if isinstance(wh, list) else wh
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
        resp = await self._session.put(
            f"{self.host}/api/config",
            params={"mode": mode, "set_changes": "true"},
        )
        resp.raise_for_status()

    async def async_set_hold(
        self, zone_id: str, activity: str, until: str | None = None
    ) -> None:
        if until is None:
            until = self.otmr_from_now(2)
        resp = await self._session.put(
            f"{self.host}/api/{zone_id}/hold",
            params={"activity": activity, "until": until},
        )
        resp.raise_for_status()

    async def async_cancel_hold(self, zone_id: str) -> None:
        resp = await self._session.put(
            f"{self.host}/api/{zone_id}/hold",
            params={"hold": "off"},
        )
        resp.raise_for_status()

    async def async_set_activity_temps(
        self, zone_id: str, activity: str, htsp: int, clsp: int
    ) -> None:
        resp = await self._session.put(
            f"{self.host}/api/{zone_id}/activity/{activity}",
            params={"htsp": str(htsp), "clsp": str(clsp)},
        )
        resp.raise_for_status()

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
        resp = await self._session.put(
            f"{self.host}/api/config/wholeHouse",
            params=params,
        )
        resp.raise_for_status()

    async def async_cancel_whole_house_hold(self) -> None:
        resp = await self._session.put(
            f"{self.host}/api/config/wholeHouse",
            params={"hold": "off", "set_changes": "true"},
        )
        resp.raise_for_status()

    async def async_save_schedule(self, zone_id: str, program: list) -> None:
        """Save full schedule for a zone via GET-modify-POST.

        The Infinitude proxy catch-all API reads query params only, not JSON
        body, so complex nested writes must go through POST /systems/infinitude
        which accepts a full JSON config and converts it back to XML.
        """
        async with self.api_lock:
            # 1. Fetch current full config
            resp = await self._session.get(f"{self.host}/systems.json")
            resp.raise_for_status()
            systems = await resp.json(content_type=None)

            # 2. Navigate to target zone — mirrors _parse() navigation exactly
            cfg = systems["system"][0]["config"][0]
            cfg_zones = self._force_array(
                cfg.get("zones", [{}])[0].get("zone") if cfg.get("zones") else []
            )

            target = None
            for z in cfg_zones:
                if str(self._v(z.get("id"))) == str(zone_id):
                    target = z
                    break

            if not target:
                _LOGGER.error("save_schedule: zone %s not found in config", zone_id)
                return

            # 3. Build day→period lookup from incoming data
            new_sched: dict[str, dict[str, dict]] = {}
            for d in program:
                new_sched[d["id"]] = {
                    str(p["id"]): p for p in d.get("period", [])
                }

            # 4. Patch periods in existing structure (preserves array wrapping)
            # program is array-wrapped like all XML::Simple nodes
            if not target.get("program"):
                _LOGGER.error("save_schedule: zone %s has no program", zone_id)
                return
            days = self._force_array(target["program"][0].get("day", []))

            for day in days:
                day_id = self._v(day.get("id"))
                if day_id not in new_sched:
                    continue
                day_periods = new_sched[day_id]
                for period in self._force_array(day.get("period", [])):
                    p_id = str(self._v(period.get("id")))
                    if p_id not in day_periods:
                        continue
                    np = day_periods[p_id]
                    # Preserve original wrapping style (list vs plain)
                    wrap = isinstance(period.get("activity"), list)
                    period["activity"] = [np["activity"]] if wrap else np["activity"]
                    period["time"] = [np["time"]] if wrap else np["time"]
                    period["enabled"] = [np["enabled"]] if wrap else np["enabled"]

            # 5. POST full config back — triggers changes flag
            resp = await self._session.post(
                f"{self.host}/systems/infinitude",
                json=systems,
            )
            resp.raise_for_status()

    async def async_set_activity_fan(
        self, zone_id: str, activity: str, fan: str
    ) -> None:
        resp = await self._session.put(
            f"{self.host}/api/{zone_id}/activity/{activity}",
            params={"fan": fan},
        )
        resp.raise_for_status()
