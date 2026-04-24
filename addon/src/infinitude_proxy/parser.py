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
    HumidityConfig,
    HvacAction,
    HvacMode,
    IduConfig,
    OduConfig,
    ScheduleDay,
    SchedulePeriod,
    SystemHoldActivity,
    VacationConfig,
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
    # Root-level thermostat state that drift detection observes to
    # confirm system_mode_set / vacation_set mutations landed. `mode` is
    # always emitted; `vacationRunning` reflects whether the active
    # vacation window is currently in effect (independent of `vacat=on`,
    # which only says one is scheduled).
    systemMode: HvacMode
    vacationRunning: bool
    zones: list[TelemetryZone]
    # Life-remaining percentages for the four reminder-tracked services.
    # None when the fixture/unit doesn't emit the field (pre-commission,
    # feature absent). Paired with ServiceConfig on the config side to
    # feed /v1/system/service.
    filterLevelPercent: int | None = None
    uvLevelPercent: int | None = None
    humidifierLevelPercent: int | None = None
    ventilatorLevelPercent: int | None = None


class ServiceConfig(BaseModel):
    """Service-reminder commissioning state from the config payload.

    Intervals are months between services (installer-configured).
    Reminder flags are the thermostat's `<*rmd>` toggles — whether the
    end-user has armed notifications for that service. `filterType` is
    the label shown on the thermostat UI; None if unset.
    """
    model_config = ConfigDict(use_enum_values=True)
    filterIntervalMonths: int
    uvIntervalMonths: int
    humidifierIntervalMonths: int
    ventilatorIntervalMonths: int
    filterReminderEnabled: bool
    uvReminderEnabled: bool
    humidifierReminderEnabled: bool
    ventilatorReminderEnabled: bool
    filterType: str | None = None


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
    vacation: VacationConfig
    humidity: HumidityConfig
    service: ServiceConfig


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


def _parse_vacation(config_el: etree._Element) -> VacationConfig:
    """Parse the vacation fields out of <config>.

    Fields are flat children of <config>, not a nested element. vacstart/
    vacend are ISO-like timestamps when set and empty strings otherwise.
    """
    def _iso(tag: str) -> datetime | None:
        t = _text(config_el, tag)
        if not t:
            return None
        try:
            return datetime.fromisoformat(t.replace("Z", "+00:00"))
        except ValueError:
            return None

    return VacationConfig(
        active=_text(config_el, "vacat") == "on",
        start=_iso("vacstart"),
        end=_iso("vacend"),
        heatSetpoint=_float_round(config_el, "vacmint") or 0,
        coolSetpoint=_float_round(config_el, "vacmaxt") or 0,
        fan=FanSpeed(_text(config_el, "vacfan") or "off"),
    )


def _parse_service(config_el: etree._Element) -> ServiceConfig:
    """Parse service-reminder intervals + flags + filter type from <config>."""
    return ServiceConfig(
        filterIntervalMonths=_int(config_el, "filterinterval") or 0,
        uvIntervalMonths=_int(config_el, "uvinterval") or 0,
        humidifierIntervalMonths=_int(config_el, "huminterval") or 0,
        ventilatorIntervalMonths=_int(config_el, "ventinterval") or 0,
        filterReminderEnabled=_text(config_el, "filtrrmd") == "on",
        uvReminderEnabled=_text(config_el, "uvrmd") == "on",
        humidifierReminderEnabled=_text(config_el, "humrmd") == "on",
        ventilatorReminderEnabled=_text(config_el, "ventrmd") == "on",
        filterType=_text(config_el, "filtertype"),
    )


def _parse_humidity(config_el: etree._Element) -> HumidityConfig:
    """Parse humidifier equipment + per-mode target RH out of <config>.

    Targets are empty on units without a humidifier — we leave them
    as None rather than zero so consumers can distinguish "no target
    configured" from "target set to 0%".
    """
    def _pct(tag: str) -> int | None:
        t = _text(config_el, tag)
        return int(t) if t is not None else None

    return HumidityConfig(
        equipmentInstalled=_text(config_el, "cfghumid") == "on",
        humidifierFan=_text(config_el, "humidityfan") == "on",
        targetHome=_pct("humidityHome"),
        targetAway=_pct("humidityAway"),
        targetVacation=_pct("humidityVacation"),
    )


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


def _lockout_temp(root: etree._Element, tag: str) -> int | None:
    """Parse a <...locktemp> field that's either "none" or a numeric degree.

    The thermostat emits the literal string "none" when the installer
    hasn't set a lockout; anything else is a Fahrenheit integer. None
    preserves the "unset" semantic; 0 would collide with a real value.
    """
    t = _text(root, tag)
    if not t or t == "none":
        return None
    try:
        return int(t)
    except ValueError:
        return None


def parse_idu_config(xml_bytes: bytes) -> IduConfig:
    """Parse POST /systems/{serial}/idu_config body.

    Most fields are commissioning knobs we don't surface (airflow CFM
    limits, furnace stages, hydronic timers, etc.). We keep the TODO
    block inline so future slices can pick off what a consumer asks for.

    TODO: known-unsurfaced fields here are candidates for later slices:
      <iduairflow>             installed airflow setting
      <gtermsetting>, label1-3 aux-terminal function + user labels
      <heatoffdelay>           blower run-on after heat call
      <reheat>, <dehumdrain>   reheat + drain-mode toggles
      <mincfm>, <maxcfm>, …    per-stage CFM commissioning
      <furnstages>             furnace stage count
      <altitudeselect>         elevation preset (paired with <elevation>)
    """
    root = etree.fromstring(xml_bytes)
    return IduConfig(
        type=_text(root, "idutype") or "",
        elevationFeet=_int(root, "elevation"),
        auxiliaryTerminalAvailable=_text(root, "gtermavail") == "on",
    )


def parse_odu_config(xml_bytes: bytes) -> OduConfig:
    """Parse POST /systems/{serial}/odu_config body.

    Surfaces identity + the three airflow profiles + lockouts + defrost
    cadence. The deep commissioning knobs (stage caps, low-ambient cool,
    brownout protection, variable-cap CFM limits) stay unsurfaced until
    a consumer asks.

    TODO: known-unsurfaced fields here are candidates for later slices:
      <coollatchmode>, <coollatchtemp>     heat-pump → aux transition
      <heatlatchmode>, <heatlatchtemp>
      <lowambcool>, <brownout>             low-ambient + brownout guards
      <mincoolstage>, <maxcoolstage>, …    per-direction stage caps
      <vcapfloorcfm>, <vcap…>              variable-capacity CFM envelope
      <flowratesetting>                    hydronic flow config
    """
    root = etree.fromstring(xml_bytes)
    return OduConfig(
        type=_text(root, "odutype") or "",
        coolAirflowProfile=_text(root, "oducoolafl") or "",
        heatAirflowProfile=_text(root, "oduheatafl") or "",
        dehumidifyAirflowProfile=_text(root, "dehumafl") or "",
        coolLockoutTemp=_lockout_temp(root, "coollocktemp"),
        heatLockoutTemp=_lockout_temp(root, "heatlocktemp"),
        defrostInterval=_text(root, "defrostInt") or "",
    )


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


def _config_from_element(config: etree._Element) -> SystemConfig:
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
    return SystemConfig(
        mode=mode,
        wholeHouseHold=wh_hold,
        zones=zones,
        vacation=_parse_vacation(config),
        humidity=_parse_humidity(config),
        service=_parse_service(config),
    )


def parse_system_config_with_tree(
    xml_bytes: bytes,
) -> tuple[etree._Element, SystemConfig]:
    """Parse a POST /systems/{serial} body, returning BOTH the raw
    <config> subtree and the typed snapshot.

    The raw tree is retained by the state store so we can serve it
    back verbatim on GET /systems/{serial}/config and mutate it in
    place when northbound writes land (Slice 2+). The thermostat's
    POST body is wrapped in <system><config>…</config></system>; we
    return the inner <config> element, which is what the GET response
    actually carries over the wire.
    """
    root = etree.fromstring(xml_bytes)
    # POST body is <system><config>...</config></system>; the serialized
    # form we persist (and serve on GET) is a bare <config>. Accept both
    # so restore-from-DB and live POSTs share one entry point.
    if root.tag == "config":
        config = root
    else:
        config = root.find("config")
        if config is None:
            raise ValueError("system XML missing <config>")
    return config, _config_from_element(config)


def reparse_config_tree(config_el: etree._Element) -> SystemConfig:
    """Re-derive the typed SystemConfig from a (possibly mutated) tree.

    Used by the replay dispatcher after applying pending writes: the
    tree has changed, so the typed snapshot we hand to /v1/state needs
    to be regenerated. Skips the xml_bytes parse step since the tree
    is already in memory.
    """
    return _config_from_element(config_el)


def parse_system_config(xml_bytes: bytes) -> SystemConfig:
    """Parse a POST /systems/{serial} body (full config dump).

    Extracts the whole-house mode + hold state and the per-zone identity
    and hold state. Activities and schedules live in the same XML but
    are surfaced via dedicated parsers/endpoints in later slices.

    TODO: known-unsurfaced fields in this payload. Each is a candidate
    for its own slice once a northbound consumer needs it:
      <config>/<utilityEvent>        utility-rate response config
      <config>/<staticPressure>      duct static pressure calibration
      <config>/<blowerSpeed>, CFM    blower commissioning data
      <config>/<filterinterval>, …   service-reminder thresholds
      zone/<otmr>, <setback>, etc.   per-zone behavior tuning knobs
    """
    _, cfg = parse_system_config_with_tree(xml_bytes)
    return cfg


def serialize_config_tree(tree: etree._Element) -> bytes:
    """Serialize the retained <config> subtree to wire bytes for GET
    /systems/{serial}/config. Matches the live Mojolicious response:
    XML declaration, newline, then the element.
    """
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        + etree.tostring(tree, encoding="utf-8")
    )


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

    Service life-remaining percentages (<filtrlvl>, <uvlvl>, <humlvl>,
    <ventlvl>) are surfaced on the snapshot so /v1/system/service can
    combine them with config-side intervals/flags. None when the unit
    doesn't emit the field.

    TODO: known-unsurfaced fields in this payload. Candidates for
    future slices once a northbound consumer asks for them:
      <status>/zone/<vacation…>      zone-scoped vacation state
      <status>/zone/<currentProgram> active schedule period id
      <status>/<cfgem>/<cfgtype>     config echo fields (forensics only)

    Equipment identity (indoor/outdoor unit type, airflow profiles,
    lockouts) is NOT in this <status> payload — it arrives as separate
    POSTs to /systems/{serial}/idu_config and /odu_config, handled by
    parse_idu_config / parse_odu_config.
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
        systemMode=HvacMode(_text(root, "mode") or "off"),
        vacationRunning=_text(root, "vacatrunning") == "on",
        zones=zones,
        filterLevelPercent=_int(root, "filtrlvl"),
        uvLevelPercent=_int(root, "uvlvl"),
        humidifierLevelPercent=_int(root, "humlvl"),
        ventilatorLevelPercent=_int(root, "ventlvl"),
    )
