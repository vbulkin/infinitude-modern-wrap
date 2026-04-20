"""Parsers from captured thermostat XML into typed snapshots.

Only the fields the proxy actually consumes. Fields like <cfgem>,
<cfgtype>, <vacatrunning> etc. are preserved in the raw bytes for
forensics but not surfaced in the snapshot.
"""

from __future__ import annotations

from datetime import datetime

from lxml import etree
from pydantic import BaseModel, ConfigDict

from .models import (
    Activity,
    ActivityId,
    DayOfWeek,
    FanSpeed,
    HvacAction,
    HvacMode,
    ScheduleDay,
    SchedulePeriod,
    SystemHoldActivity,
    WholeHouseHold,
    ZoneHold,
)


# Thermostat <zoneconditioning> wire values → our HvacAction enum.
# Values observed in live fixtures + defensive coverage for the
# remaining heat/cool/dehumidify variants documented in the design.
_CONDITIONING_MAP = {
    "idle": HvacAction.IDLE,
    "off": HvacAction.OFF,
    "active_heat": HvacAction.HEATING,
    "staged1_heat": HvacAction.HEATING,
    "staged2_heat": HvacAction.HEATING,
    "active_cool": HvacAction.COOLING,
    "staged1_cool": HvacAction.COOLING,
    "staged2_cool": HvacAction.COOLING,
    "dehumidify": HvacAction.DEHUMIDIFYING,
    "fan": HvacAction.FAN,
}


def _text(el: etree._Element, tag: str) -> str | None:
    found = el.find(tag)
    if found is None:
        return None
    txt = found.text
    return txt.strip() if txt and txt.strip() else None


def _int(el: etree._Element, tag: str) -> int | None:
    t = _text(el, tag)
    return int(t) if t is not None else None


def _float_round(el: etree._Element, tag: str) -> int | None:
    t = _text(el, tag)
    return round(float(t)) if t is not None else None


class TelemetryZone(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: str
    name: str
    enabled: bool
    temperature: int
    humidity: int
    heatSetpoint: int
    coolSetpoint: int
    fan: FanSpeed
    damperPercent: int
    conditioning: HvacAction
    currentActivity: ActivityId
    holdActive: bool


class TelemetrySnapshot(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    localTime: datetime
    outdoorTemperature: int
    operatingStatusMessage: str
    humidifierOn: bool
    zones: list[TelemetryZone]


class ZoneConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: str
    name: str
    enabled: bool
    hold: ZoneHold
    activities: list[Activity]
    schedule: list[ScheduleDay]


class SystemConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    mode: HvacMode
    wholeHouseHold: WholeHouseHold
    zones: list[ZoneConfig]


def _parse_whole_house_hold(wh: etree._Element | None) -> WholeHouseHold:
    if wh is None:
        return WholeHouseHold(active=False)
    active = _text(wh, "hold") == "on"
    raw = _text(wh, "holdActivity")
    activity: SystemHoldActivity | None = None
    if raw and raw != "none":
        try:
            activity = SystemHoldActivity(raw)
        except ValueError:
            activity = None
    return WholeHouseHold(active=active, activity=activity, until=None)


def _parse_activities(zone_el: etree._Element) -> list[Activity]:
    """Parse <zone>/<activities>/<activity id="..."> entries.

    Unknown ids are dropped (we keep ActivityId as a closed enum on
    the API surface). Setpoints come in as float strings; we round
    to the ints our Temperature type requires.
    """
    out: list[Activity] = []
    acts_el = zone_el.find("activities")
    if acts_el is None:
        return out
    for a in acts_el.findall("activity"):
        raw_id = a.get("id") or ""
        try:
            aid = ActivityId(raw_id)
        except ValueError:
            continue
        out.append(
            Activity(
                id=aid,
                heat=_float_round(a, "htsp") or 0,
                cool=_float_round(a, "clsp") or 0,
                fan=FanSpeed(_text(a, "fan") or "off"),
            )
        )
    return out


def _parse_schedule(zone_el: etree._Element) -> list[ScheduleDay]:
    """Parse <zone>/<program>/<day id="Sunday"><period id="N">...

    Seven days, up to five periods each. Period activity references
    must resolve against ActivityId; unknown ids drop the period.
    """
    out: list[ScheduleDay] = []
    prog = zone_el.find("program")
    if prog is None:
        return out
    for d in prog.findall("day"):
        raw_day = d.get("id") or ""
        try:
            day = DayOfWeek(raw_day)
        except ValueError:
            continue
        periods: list[SchedulePeriod] = []
        for p in d.findall("period"):
            raw_id = p.get("id") or ""
            try:
                pid = int(raw_id)
            except ValueError:
                continue
            raw_act = _text(p, "activity") or ""
            try:
                act = ActivityId(raw_act)
            except ValueError:
                continue
            periods.append(
                SchedulePeriod(
                    id=pid,
                    activity=act,
                    time=_text(p, "time") or "00:00",
                    enabled=_text(p, "enabled") == "on",
                )
            )
        if periods:
            out.append(ScheduleDay(day=day, periods=periods))
    return out


def _parse_zone_hold(zone_el: etree._Element) -> ZoneHold:
    active = _text(zone_el, "hold") == "on"
    raw = _text(zone_el, "holdActivity")
    activity: ActivityId | None = None
    if raw and raw not in ("none", ""):
        try:
            activity = ActivityId(raw)
        except ValueError:
            activity = None
    return ZoneHold(active=active, activity=activity, until=None)


def parse_system_config(xml_bytes: bytes) -> SystemConfig:
    """Parse a POST /systems/{serial} body (full config dump).

    Extracts the whole-house mode + hold state and the per-zone identity
    and hold state. Activities and schedules live in the same XML but
    are surfaced via dedicated parsers/endpoints in later slices.

    TODO: known-unsurfaced fields in this payload. Each is a candidate
    for its own slice once a northbound consumer needs it:
      <config>/<vacation>            vacation hold window + setpoints
      <config>/<humidityConfig>      humidifier/dehumidifier targets
      <config>/<utility>             utility-rate response config
      <config>/<staticPressure>      duct static pressure calibration
      zone/<otmr>, <setback>, etc.   per-zone behavior tuning knobs
    """
    root = etree.fromstring(xml_bytes)
    config = root.find("config")
    if config is None:
        raise ValueError("system XML missing <config>")

    mode = HvacMode(_text(config, "mode") or "off")
    wh_hold = _parse_whole_house_hold(config.find("wholeHouse"))

    zones: list[ZoneConfig] = []
    zones_el = config.find("zones")
    if zones_el is not None:
        for z in zones_el.findall("zone"):
            if _text(z, "enabled") != "on":
                continue
            zones.append(
                ZoneConfig(
                    id=z.get("id") or "",
                    name=_text(z, "name") or "",
                    enabled=True,
                    hold=_parse_zone_hold(z),
                    activities=_parse_activities(z),
                    schedule=_parse_schedule(z),
                )
            )
    return SystemConfig(mode=mode, wholeHouseHold=wh_hold, zones=zones)


class NotificationChange(BaseModel):
    id: str
    zone: str | None = None


class NotificationEvent(BaseModel):
    type: str
    code: int
    message: str
    timestamp: datetime
    changes: list[NotificationChange]


def parse_notifications(xml_bytes: bytes) -> list[NotificationEvent]:
    """Parse a POST /systems/{serial}/notifications body.

    One <notifications> envelope can carry multiple <notification>
    children; each in turn can list multiple <change> entries.
    """
    root = etree.fromstring(xml_bytes)
    events: list[NotificationEvent] = []
    for n in root.findall("notification"):
        changes_el = n.find("changes")
        changes: list[NotificationChange] = []
        if changes_el is not None:
            for c in changes_el.findall("change"):
                changes.append(
                    NotificationChange(id=c.get("id") or "", zone=c.get("zone"))
                )
        events.append(
            NotificationEvent(
                type=_text(n, "type") or "",
                code=int(_text(n, "code") or "0"),
                message=_text(n, "message") or "",
                timestamp=datetime.fromisoformat(
                    (_text(n, "timestamp") or "").replace("Z", "+00:00")
                ),
                changes=changes,
            )
        )
    return events


def parse_telemetry(xml_bytes: bytes) -> TelemetrySnapshot:
    """Parse a POST /systems/{serial}/status body into a snapshot.

    Damper: thermostat reports 0–15; we normalize to 0–100% at this
    boundary per the design decision (see design/DESIGN.md §6).

    TODO: known-unsurfaced fields in this payload. Candidates for
    future slices once a northbound consumer asks for them:
      <status>/<idu>                 indoor-unit runtime telemetry
      <status>/<odu>                 outdoor-unit runtime telemetry
      <status>/zone/<vacation…>      zone-scoped vacation state
      <status>/zone/<currentProgram> active schedule period id
      <status>/<cfgem>/<cfgtype>     config echo fields (forensics only)
      <status>/<vacatrunning>        vacation-in-progress flag
    """
    root = etree.fromstring(xml_bytes)
    zones: list[TelemetryZone] = []
    zones_el = root.find("zones")
    if zones_el is not None:
        for z in zones_el.findall("zone"):
            if _text(z, "enabled") != "on":
                continue
            damper_raw = _int(z, "damperposition") or 0
            zones.append(
                TelemetryZone(
                    id=z.get("id") or "",
                    name=_text(z, "name") or "",
                    enabled=True,
                    temperature=_float_round(z, "rt") or 0,
                    humidity=_int(z, "rh") or 0,
                    heatSetpoint=_float_round(z, "htsp") or 0,
                    coolSetpoint=_float_round(z, "clsp") or 0,
                    fan=FanSpeed(_text(z, "fan") or "off"),
                    damperPercent=round(damper_raw * 100 / 15),
                    conditioning=_CONDITIONING_MAP.get(
                        _text(z, "zoneconditioning") or "idle", HvacAction.IDLE
                    ),
                    currentActivity=ActivityId(_text(z, "currentActivity") or "home"),
                    holdActive=_text(z, "hold") == "on",
                )
            )
    return TelemetrySnapshot(
        localTime=datetime.fromisoformat(
            (_text(root, "localTime") or "").replace("Z", "+00:00")
        ),
        outdoorTemperature=_int(root, "oat") or 0,
        operatingStatusMessage=_text(root, "oprstsmsg") or "",
        humidifierOn=_text(root, "humid") == "on",
        zones=zones,
    )
