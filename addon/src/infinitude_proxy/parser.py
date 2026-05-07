"""Parsers from captured thermostat XML into typed snapshots.

Only the fields the proxy actually consumes. Fields like <cfgem>,
<cfgtype>, <vacatrunning> etc. are preserved in the raw bytes for
forensics but not surfaced in the snapshot.
"""

from __future__ import annotations

import logging
from datetime import datetime

from lxml import etree
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


def _coerce_hvac_mode(raw: str, *, where: str) -> "HvacMode":
    """Map a thermostat-reported HVAC mode to our enum, tolerating values
    we haven't catalogued yet.

    The thermostat reports operational modes in telemetry's <mode> element
    (e.g. "hpheat" for heat-pump heating) that are distinct from the
    user-selectable config modes. Crashing the entire status pipeline
    because one heat-pump install reports an unfamiliar string is the
    wrong default — log it once at INFO and fall back to "off" so the
    rest of the snapshot still lands.
    """
    raw = (raw or "").strip()
    if not raw:
        return HvacMode.OFF
    try:
        return HvacMode(raw)
    except ValueError:
        logger.info(
            "parser: unknown HVAC mode %r at %s — coercing to 'off'", raw, where
        )
        return HvacMode.OFF

from .models import (
    Activity,
    ActivityId,
    DayOfWeek,
    Energy,
    EnergyModeFlags,
    EnergyPeriod,
    EquipmentEvent,
    EquipmentEvents,
    FanSpeed,
    HumidityConfig,
    HvacAction,
    HvacMode,
    IduConfig,
    IduStatus,
    OduConfig,
    OduStatus,
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
    # 1 or 2 when the thermostat reports a staged condition
    # (`staged1_heat`, `staged2_cool`, etc.) — multi-stage HP/AC.
    # None for `active_*` (single-stage) or idle. Surfaced via
    # `_build_zone` as Zone.conditioningStage so HA consumers see
    # capacity stage without re-parsing strings.
    conditioningStage: int | None = None
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
    until = _text(wh, "otmr") or None
    return WholeHouseHold(active=active, activity=activity, until=until)


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
    until = _text(zone_el, "otmr") or None
    return ZoneHold(active=active, activity=activity, until=until)


def _config_from_element(config: etree._Element) -> SystemConfig:
    mode = _coerce_hvac_mode(_text(config, "mode") or "off", where="config.mode")
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


def serialize_system_post_body(
    config_tree: etree._Element, *, system_version: str = "1.7",
) -> bytes:
    """Build a thermostat-style boot POST body for `POST /systems/{serial}`.

    The thermostat's wire format (observed in live captures, e.g.
    `addon/tests/fixtures/thermostat/boot_01_system_config.xml`) is:

        Content-Type: application/x-www-form-urlencoded
        body:        data=<URL-encoded XML>

    where the unwrapped XML is `<system version="1.7"><config>...</config></system>`.
    `config_tree` is the bare `<config>` element our state store retains.

    This helper synthesizes the full wire-format body so the addon can
    POST it back upstream to Carrier — see `CarrierBridge.push_config`.
    Carrier originally learned the device's config from the thermostat's
    real boot POST; we replay that exact shape so Carrier accepts it as
    a legitimate device-side config sync after an HA mutation.
    """
    inner_xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<system version="' + system_version.encode("ascii") + b'">'
        + etree.tostring(config_tree, encoding="utf-8")
        + b'</system>'
    )
    # `quote_from_bytes` matches the thermostat's URL-encoding (RFC
    # 3986 reserved set). The body is form-shape `data=<encoded>`.
    from urllib.parse import quote_from_bytes
    return b"data=" + quote_from_bytes(inner_xml).encode("ascii")


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
                    conditioningStage=_extract_stage(
                        _text(z, "zoneconditioning") or ""
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
        systemMode=_coerce_hvac_mode(
            _text(root, "mode") or "off", where="telemetry.mode"
        ),
        vacationRunning=_text(root, "vacatrunning") == "on",
        zones=zones,
        filterLevelPercent=_int(root, "filtrlvl"),
        uvLevelPercent=_int(root, "uvlvl"),
        humidifierLevelPercent=_int(root, "humlvl"),
        ventilatorLevelPercent=_int(root, "ventlvl"),
    )


def _extract_stage(zoneconditioning: str) -> int | None:
    """Pull the 1/2 stage suffix out of `staged1_heat` / `staged2_cool`
    etc. Returns None for `active_*`, `idle`, `off`, or anything we
    don't recognize — the conditioning enum already collapses those."""
    if zoneconditioning.startswith("staged1_"):
        return 1
    if zoneconditioning.startswith("staged2_"):
        return 2
    return None


# ── Energy (per-mode runtime hours + efficiency ratings) ─────────────

_ENERGY_MODES: tuple[str, ...] = (
    "cooling", "hpheat", "eheat", "gas", "reheat", "fangas", "fan", "looppump",
)
_ENERGY_PERIOD_IDS: tuple[str, ...] = (
    "day1", "day2", "month1", "month2", "year1", "year2",
)


def _on_off_attr(el: etree._Element, name: str) -> bool:
    """Coerce thermostat's `on|off` attribute style to bool."""
    v = (el.get(name) or "").strip().lower()
    return v == "on"


def _opt_float(el: etree._Element, tag: str) -> float | None:
    """Inner text → float, or None if missing/blank/non-numeric.
    Used for the energy ratings (seer/hspf), which are decimals like
    `15.0` / `8.8`."""
    raw = _text(el, tag)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_energy(xml_bytes: bytes) -> Energy:
    """Parse the thermostat's `<energy>` snapshot (POSTed at
    `/systems/{serial}/energy`).

    Two halves:
      * Static config — SEER/HSPF ratings + per-mode display/enabled
        flags as empty elements with attributes.
      * Usage — `<period id="dayN|monthN|yearN">` blocks with one
        integer per mode. Hour counters; periods named day1/2 (today
        / yesterday), month1/2 (this / last month), year1/2 (this /
        last year). Values default to 0 when absent.

    Unknown periods are skipped, unknown modes are ignored — keeps
    the parser tolerant of firmware that surfaces additional fields.
    """
    root = etree.fromstring(xml_bytes)
    modes: dict[str, EnergyModeFlags] = {}
    for name in _ENERGY_MODES:
        el = root.find(name)
        if el is None:
            continue
        modes[name] = EnergyModeFlags(
            display=_on_off_attr(el, "display"),
            enabled=_on_off_attr(el, "enabled"),
        )

    usage: list[EnergyPeriod] = []
    usage_el = root.find("usage")
    if usage_el is not None:
        for period in usage_el.findall("period"):
            pid = period.get("id") or ""
            if pid not in _ENERGY_PERIOD_IDS:
                continue
            counters: dict[str, int] = {}
            for mode in _ENERGY_MODES:
                raw = _text(period, mode)
                if raw:
                    try:
                        counters[mode] = int(raw)
                    except ValueError:
                        counters[mode] = 0
            usage.append(EnergyPeriod(id=pid, **counters))

    return Energy(
        seer=_opt_float(root, "seer"),
        hspf=_opt_float(root, "hspf"),
        modes=modes,
        usage=usage,
    )


# ── Equipment events (fault history) ──────────────────────────────────

def parse_equipment_events(xml_bytes: bytes) -> EquipmentEvents:
    """Parse `<equipment_events>` (POSTed at
    `/systems/{serial}/equipment_events`).

    Each `<event>` carries: id (per-event ordinal), code (numeric
    fault code), source (zone or unit identifier — `ZN1` / `IDU` /
    `ODU` etc.), description (free-text), localtime (thermostat-local
    timestamp, no tz suffix), occurrences (counter), active (`on|off`).
    """
    root = etree.fromstring(xml_bytes)
    events: list[EquipmentEvent] = []
    events_el = root.find("events")
    if events_el is not None:
        for ev in events_el.findall("event"):
            events.append(EquipmentEvent(
                id=ev.get("id") or "",
                code=_text(ev, "code") or "",
                source=_text(ev, "source") or "",
                description=_text(ev, "description") or "",
                localTime=_text(ev, "localtime") or "",
                occurrences=int(_text(ev, "occurrences") or "0"),
                active=_text(ev, "active") == "on",
            ))
    return EquipmentEvents(events=events)


# ── ODU / IDU live status ─────────────────────────────────────────────
# Helpers to coerce the thermostat's placeholder strings (`na`,
# `invalid`, `none`, empty) to None on numeric fields. The unit only
# emits real values for sensors that are reading; idle sensors stay
# empty / placeholder until the unit cycles on.

_NUMERIC_PLACEHOLDERS = frozenset({"na", "invalid", "none", "n/a", ""})


def _opt_int_text(el: etree._Element, tag: str) -> int | None:
    raw = (_text(el, tag) or "").strip().lower()
    if raw in _NUMERIC_PLACEHOLDERS:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _opt_float_text(el: etree._Element, tag: str) -> float | None:
    raw = (_text(el, tag) or "").strip().lower()
    if raw in _NUMERIC_PLACEHOLDERS:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_stage(opstat: str) -> int | None:
    """Pull the `N` out of `Stage N` opstat strings; everything else
    returns None (`off`, `idle`, etc. → not a stage).

    Examples:
      "Stage 0" → 0   (idle compressor)
      "Stage 1" → 1   (low-capacity)
      "Stage 2" → 2   (high-capacity)
      "off"     → None
    """
    parts = (opstat or "").strip().split()
    if len(parts) == 2 and parts[0].lower() == "stage":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def parse_odu_status(xml_bytes: bytes) -> OduStatus:
    """Parse `<odu_status>` POSTed by the thermostat at
    `/systems/{serial}/odu_status`. Live runtime state for the outdoor
    unit — compressor stage + RPM, refrigerant pressures, blower
    state, etc. Idle-state sensors arrive as `na`/`invalid`/empty
    elements; coerced to None."""
    root = etree.fromstring(xml_bytes)
    opstat = (_text(root, "opstat") or "").strip()
    return OduStatus(
        odutype=_text(root, "odutype") or "",
        opstat=opstat,
        operatingStage=_parse_stage(opstat),
        opmode=_text(root, "opmode") or "off",
        outdoorTemperature=_opt_int_text(root, "oat"),
        blowerRpm=_opt_int_text(root, "blwrpm"),
        iduCfm=_opt_int_text(root, "iducfm"),
        coilTemperature=_opt_int_text(root, "oducoiltmp"),
        leavingAirTemperature=_opt_int_text(root, "lat"),
        lineVoltage=_opt_int_text(root, "linevolt"),
        lockoutActive=_text(root, "lockactive") == "on",
        lockoutTime=_opt_int_text(root, "locktime"),
        compressorRpm=_opt_int_text(root, "comprpm"),
        suctionPressure=_opt_float_text(root, "suctpress"),
        suctionTemperature=_opt_int_text(root, "sucttemp"),
        suctionSuperheat=_opt_float_text(root, "suctsupheat"),
        dischargeTemperature=_opt_int_text(root, "dischargetmp"),
        spareSensorStatus=_text(root, "sparesensorstatus") or None,
        spareSensorValue=_opt_float_text(root, "sparesensorvalue"),
        expansionValvePosition=_opt_int_text(root, "exvpos"),
        curtailActive=_text(root, "curtail") == "on",
        staticPressure=_opt_float_text(root, "statpress"),
        enteringRefrigerantTemperature=_opt_float_text(root, "enterreftmp"),
        availMinHeatStage=_opt_int_text(root, "availminheatstage"),
        availMaxHeatStage=_opt_int_text(root, "availmaxheatstage"),
        availMinCoolStage=_opt_int_text(root, "availmincoolstage"),
        availMaxCoolStage=_opt_int_text(root, "availmaxcoolstage"),
        opMinHeatStage=_opt_int_text(root, "opminheatstage"),
        opMaxHeatStage=_opt_int_text(root, "opmaxheatstage"),
        opMinCoolStage=_opt_int_text(root, "opmincoolstage"),
        opMaxCoolStage=_opt_int_text(root, "opmaxcoolstage"),
    )


def parse_idu_status(xml_bytes: bytes) -> IduStatus:
    """Parse `<idu_status>` POSTed at `/systems/{serial}/idu_status`.
    Runtime state for the indoor unit — blower RPM, airflow, static
    pressure, coil temp.

    Note: `<lockouttime>` is a string here (vs. ODU's int `<locktime>`).
    On a fancoil it's `"off"` when not locked; some firmware variants
    may emit a duration string when locked. We pass it through verbatim.
    """
    root = etree.fromstring(xml_bytes)
    opstat = (_text(root, "opstat") or "").strip()
    lockout_raw = _text(root, "lockouttime")
    return IduStatus(
        idutype=_text(root, "idutype") or "",
        pwmBlower=_text(root, "pwmblower") == "on",
        opstat=opstat,
        operatingStage=_parse_stage(opstat),
        iduCfm=_opt_int_text(root, "iducfm"),
        blowerRpm=_opt_int_text(root, "blwrpm"),
        staticPressure=_opt_float_text(root, "statpress"),
        coilTemperature=_opt_int_text(root, "coiltemp"),
        inducerRpm=_opt_int_text(root, "inducerrpm"),
        leavingAirTemperature=_opt_int_text(root, "lat"),
        lockoutActive=_text(root, "lockoutactive") == "on",
        lockoutTime=lockout_raw or None,
    )
