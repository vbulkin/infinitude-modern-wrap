"""Pydantic v2 models for the Infinitude Modern Proxy API.

Source of truth for the wire format is design/openapi.yaml. These models must
stay in sync; a Phase 3 contract test will assert the FastAPI-generated
OpenAPI matches the hand-authored spec.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
    StringConstraints,
    model_validator,
)


# PATCH/PUT bodies declare nullable fields as `T | None = None` so callers can
# omit them to leave the field unchanged. Per the OpenAPI contract most of
# these fields are non-nullable — a caller sending an explicit JSON `null`
# is a type error, not "clear the field". This validator strips keys whose
# value is `None` from the incoming dict *before* Pydantic parses it, so
# omission and explicit-null both map to "unchanged" … except when the
# field is declared nullable in the spec, in which case explicit-null must
# be preserved. We list the exception set per model via `NULLABLE_FIELDS`.


def _reject_explicit_null(
    data: dict, *, nullable_fields: frozenset[str] = frozenset()
) -> dict:
    """Reject explicit JSON `null` for fields not in `nullable_fields`.

    Fields *omitted* from the body are fine — they stay "unchanged".
    """
    if not isinstance(data, dict):
        return data
    bad = [k for k, v in data.items() if v is None and k not in nullable_fields]
    if bad:
        raise ValueError(
            "Field(s) may not be null (omit to leave unchanged): "
            + ", ".join(sorted(bad))
        )
    return data


def _parse_iso_datetime_strict(v):
    """Replace Pydantic's default datetime coercion with strict ISO-8601.

    Pydantic's default accepts numeric input as a Unix epoch timestamp —
    not our wire contract. A bare `"0"` as a query param would silently
    become 1970-01-01. Require a proper ISO-8601 datetime string (or an
    existing datetime instance) and reject everything else.
    """
    if isinstance(v, datetime):
        return v
    if isinstance(v, bool) or isinstance(v, (int, float)):
        raise ValueError(
            "Expected an ISO-8601 datetime string; numeric input is not accepted."
        )
    if not isinstance(v, str):
        raise ValueError("Expected an ISO-8601 datetime string.")
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Invalid ISO-8601 datetime: {e}") from e


StrictIsoDatetime = Annotated[datetime, PlainValidator(_parse_iso_datetime_strict)]


def _iso_utc_z(dt: datetime | None) -> str | None:
    """Serialize a datetime as `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` (UTC, Z-suffixed).

    Naive datetimes are assumed UTC (consistent with our parser/mutation
    layers). Aware datetimes are normalized to UTC. Microseconds are
    preserved when non-zero so clients using `receivedAt` as a
    reconnect cursor don't lose precision in the round trip.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    if dt.microsecond:
        base = f"{base}.{dt.microsecond:06d}"
    return f"{base}Z"


IsoDatetimeOut = Annotated[
    datetime,
    PlainSerializer(_iso_utc_z, return_type=str, when_used="json"),
]


def _reject_bool_as_int(v):
    """Pydantic treats `bool` as `int` (because Python's `bool` subclasses
    `int`), so `Field(ge=0, le=100)` happily accepts `True`/`False`.
    Reject bool input at the wire — booleans are not percentages."""
    if isinstance(v, bool):
        raise ValueError("Expected integer; boolean is not accepted.")
    return v


# ── Scalar / enum types ──────────────────────────────────────────────

class HvacMode(str, Enum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    AUTO = "auto"
    FAN_ONLY = "fanonly"
    # Operational modes the thermostat reports in *telemetry's* <mode>
    # element — these never appear as user-selectable config modes, but
    # the southbound status parser still has to round-trip them without
    # crashing. Listed here so the enum coerce succeeds on known
    # values; anything novel falls through `_coerce_hvac_mode` which
    # logs and defaults to OFF rather than 500'ing the entire status
    # path.
    #   hpheat     — heat-pump active heating
    #   hpcool     — heat-pump active cooling
    #   dehumidify — cooling cycle running for moisture removal
    #   defrost    — heat-pump reverse-cycle defrost
    #   emheat     — emergency / aux electric heat
    HP_HEAT = "hpheat"
    HP_COOL = "hpcool"
    DEHUMIDIFY = "dehumidify"
    DEFROST = "defrost"
    EM_HEAT = "emheat"


class HvacAction(str, Enum):
    IDLE = "idle"
    HEATING = "heating"
    COOLING = "cooling"
    DEHUMIDIFYING = "dehumidifying"
    FAN = "fan"
    OFF = "off"


class FanSpeed(str, Enum):
    OFF = "off"
    LOW = "low"
    MED = "med"
    HIGH = "high"


class ActivityId(str, Enum):
    HOME = "home"
    AWAY = "away"
    SLEEP = "sleep"
    WAKE = "wake"
    MANUAL = "manual"


class SystemHoldActivity(str, Enum):
    HOME = "home"
    AWAY = "away"
    SLEEP = "sleep"
    WAKE = "wake"


class DayOfWeek(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


Temperature = Annotated[int, Field(ge=45, le=99)]
PercentInt = Annotated[int, BeforeValidator(_reject_bool_as_int), Field(ge=0, le=100)]
ZoneIdStr = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]*$")]
LocalWallTime = Annotated[str, StringConstraints(pattern=r"^(?:[01][0-9]|2[0-3]):(?:[0-5][0-9])$")]


# ── Errors ───────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    path: str
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


# ── Holds ────────────────────────────────────────────────────────────

class ZoneHold(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    active: bool
    activity: ActivityId | None = None
    until: LocalWallTime | None = None


class WholeHouseHold(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    active: bool
    activity: SystemHoldActivity | None = None
    until: LocalWallTime | None = None


class ZoneHoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    activity: ActivityId
    until: LocalWallTime | None = None


class WholeHouseHoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    activity: SystemHoldActivity
    until: LocalWallTime | None = None


# ── System / zones / activities / schedule ───────────────────────────

class System(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    mode: HvacMode
    outdoorTemperature: int | None = None
    humidifierOn: bool | None = None
    lastReportAt: IsoDatetimeOut | None = None
    operatingStatusMessage: str | None = None
    serial: str
    hold: WholeHouseHold


class SystemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    mode: HvacMode | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_null_fields(cls, data):
        return _reject_explicit_null(data)


class Zone(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: ZoneIdStr
    name: str
    enabled: bool
    temperature: int | None = None
    humidity: PercentInt | None = None
    heatSetpoint: Temperature | None = None
    coolSetpoint: Temperature | None = None
    fan: FanSpeed | None = None
    damperPercent: PercentInt | None = None
    conditioning: HvacAction | None = None
    # Compressor stage when conditioning is staged (multi-stage HP/AC).
    # 1 = first stage (low capacity), 2 = second stage (high capacity).
    # None when single-stage `active_*` or idle. Derived from telemetry's
    # `<zoneconditioning>` text — staged1_heat/staged2_heat,
    # staged1_cool/staged2_cool. Surfaced as a separate field so HA
    # consumers can map to attributes without re-parsing strings.
    conditioningStage: Literal[1, 2] | None = None
    currentActivity: ActivityId | None = None
    hold: ZoneHold


class ZonePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heat: Temperature | None = None
    cool: Temperature | None = None
    activateHold: Annotated[bool, Field(strict=True)] = True

    @model_validator(mode="before")
    @classmethod
    def _no_null_fields(cls, data):
        return _reject_explicit_null(data)


class Activity(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: ActivityId
    heat: Temperature
    cool: Temperature
    fan: FanSpeed


class ActivityPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    heat: Temperature | None = None
    cool: Temperature | None = None
    fan: FanSpeed | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_null_fields(cls, data):
        return _reject_explicit_null(data)


class SchedulePeriod(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: Annotated[int, Field(ge=1, le=5)]
    activity: ActivityId
    time: LocalWallTime
    enabled: bool


class ScheduleDay(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    day: DayOfWeek
    periods: Annotated[list[SchedulePeriod], Field(min_length=1, max_length=5)]


class Schedule(BaseModel):
    zoneId: ZoneIdStr
    days: Annotated[list[ScheduleDay], Field(min_length=7, max_length=7)]


class SchedulePut(BaseModel):
    """Full-schedule overwrite. Zone id comes from the path, not the body —
    keeping it out avoids silent path/body mismatches. Must supply all seven
    days (list min_length=7); endpoint additionally validates uniqueness of
    day names so no day is duplicated or omitted."""
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    days: Annotated[list[ScheduleDay], Field(min_length=7, max_length=7)]


# ── System-level equipment config ────────────────────────────────────

class VacationConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    active: bool
    start: IsoDatetimeOut | None = None
    end: IsoDatetimeOut | None = None
    heatSetpoint: Temperature
    coolSetpoint: Temperature
    fan: FanSpeed


class VacationPatch(BaseModel):
    """Writable subset of VacationConfig. All fields optional — sparse
    update. At least one must be supplied (empty body rejected at
    endpoint). `start`/`end` may be cleared by sending `null`; other
    fields must be omitted (not sent as null) to be left unchanged.
    """
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    active: Annotated[bool, Field(strict=True)] | None = None
    start: StrictIsoDatetime | None = None
    end: StrictIsoDatetime | None = None
    heatSetpoint: Temperature | None = None
    coolSetpoint: Temperature | None = None
    fan: FanSpeed | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_null_fields(cls, data):
        return _reject_explicit_null(
            data, nullable_fields=frozenset({"start", "end"})
        )


class ServiceReminderItem(BaseModel):
    """One service-reminder entry.

    `intervalMonths` is the installer-configured servicing cadence.
    `reminderEnabled` reflects the thermostat's `<*rmd>` flag — whether
    the user has armed the reminder for this service. `levelPercent` is
    the telemetry-reported life remaining (0–100, where 0 means due);
    None means no telemetry has landed yet.
    """
    reminderEnabled: bool
    intervalMonths: Annotated[int, Field(ge=0)]
    levelPercent: PercentInt | None = None


class FilterReminder(ServiceReminderItem):
    """Filter reminder adds a human-readable filter-type label from config
    (`<filtertype>`, e.g. "air filter", "media filter"). None when the
    installer hasn't set one."""
    filterType: str | None = None


class ServiceReminders(BaseModel):
    """Combined service-reminder view: config-driven intervals/flags plus
    telemetry-driven life-remaining levels. Read-only — intervals and
    reminder flags are commissioning data, not user-tunable through our API."""
    filter: FilterReminder
    uv: ServiceReminderItem
    humidifier: ServiceReminderItem
    ventilator: ServiceReminderItem


class HumidityConfig(BaseModel):
    """Humidifier equipment + per-mode target RH.

    Targets are Optional because units without a humidifier configured
    leave the fields empty in the wire payload. `equipmentInstalled`
    reflects `<cfghumid>on</cfghumid>` — the presence of the hardware,
    not whether any target is set.
    """
    equipmentInstalled: bool
    humidifierFan: bool
    targetHome: PercentInt | None = None
    targetAway: PercentInt | None = None
    targetVacation: PercentInt | None = None


class HumidityPatch(BaseModel):
    """Writable subset of HumidityConfig — per-mode target RH.

    Only the targets are writable; `equipmentInstalled` is a commissioning
    fact, not a user preference. At least one target must be supplied —
    an empty body is rejected with 422 at the endpoint. Targets are
    non-nullable: omit to leave unchanged; an explicit `null` is a
    type error.
    """
    model_config = ConfigDict(extra="forbid")
    targetHome: PercentInt | None = None
    targetAway: PercentInt | None = None
    targetVacation: PercentInt | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_null_fields(cls, data):
        return _reject_explicit_null(data)


class IduConfig(BaseModel):
    """Indoor-unit equipment identity + commissioning knobs.

    `type` is the wire string (e.g., "fancoilelectric", "furnace") kept
    open because the installer base is broad and we don't want parsing
    to fail when a new idutype ships. `elevationFeet` is None on units
    where the installer left it at defaults; zero is a legitimate value
    at sea level, so None means "unset" not "ground".
    """
    type: str
    elevationFeet: int | None = None
    auxiliaryTerminalAvailable: bool


class NotificationChangeEntry(BaseModel):
    id: str
    zone: str | None = None


class NotificationBody(BaseModel):
    """Thermostat notification event body.

    Mirrors what the thermostat sends in a POST /notifications body —
    `type` is always "confirmation" in observed traffic but is left
    open so we don't drop future alert/warning shapes. `timestamp` is
    the thermostat's wall-clock at emission; `receivedAt` on the
    envelope is ours.
    """
    type: str
    code: int
    message: str
    timestamp: IsoDatetimeOut
    changes: list[NotificationChangeEntry]


class NotificationEnvelope(BaseModel):
    """Stored-and-served notification: a body plus our receive metadata.

    Same shape the SSE stream emits for each `notification` event.
    Clients doing reconnect backfill (/v1/notifications?since=…) use
    `receivedAt` as their cursor — the thermostat's own `timestamp`
    can go backwards across resets, so it's not a reliable ordering
    key on its own.
    """
    serial: str
    receivedAt: IsoDatetimeOut
    event: NotificationBody


class OduConfig(BaseModel):
    """Outdoor-unit equipment identity + airflow/lockout config.

    Airflow profiles are wire strings ("comfort", "efficiency", etc.);
    we don't enum them for the same forward-compat reason as IDU type.
    Lockout temps are Optional — the thermostat reports "none" when the
    installer hasn't set a threshold, which we round-trip as None rather
    than coerce to a sentinel int.
    """
    type: str
    coolAirflowProfile: str
    heatAirflowProfile: str
    dehumidifyAirflowProfile: str
    coolLockoutTemp: int | None = None
    heatLockoutTemp: int | None = None
    defrostInterval: str


# ── State + events ───────────────────────────────────────────────────

class State(BaseModel):
    system: System
    zones: list[Zone]
    lastUpdated: IsoDatetimeOut


class StateUpdatePayload(BaseModel):
    resource: str
    changes: dict


class HealthChangedPayload(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    reason: str | None = None


class HoldChangedPayload(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    resource: str
    state: Literal["active", "cleared"]
    activity: ActivityId | None = None
    until: IsoDatetimeOut | None = None


# ── Health ───────────────────────────────────────────────────────────

class ThermostatHealth(BaseModel):
    status: Literal["healthy", "stale", "unreachable"]
    lastContact: IsoDatetimeOut | None = None
    lastContactAgeSeconds: Annotated[int, Field(ge=0)] | None = None
    expectedIntervalSeconds: Annotated[int, Field(ge=1)]
    staleThresholdSeconds: Annotated[int, Field(ge=1)]


class CarrierCloudHealth(BaseModel):
    # `unknown` = bridge enabled but no relay attempted yet (process
    # just started, or no thermostat traffic recently). Distinguishes
    # "we haven't tried" from "we tried and failed" (degraded /
    # unreachable). UI consumers should treat unknown as neutral
    # (yellow/grey), not red.
    status: Literal["healthy", "degraded", "unreachable", "disabled", "unknown"]
    lastSuccess: IsoDatetimeOut | None = None
    lastAttempt: IsoDatetimeOut | None = None
    lastError: str | None = None
    passReqsIntervalSeconds: Annotated[int, Field(ge=10, le=3600)]
    consecutiveFailures: Annotated[int, Field(ge=0)]


class MutationDriftEvent(BaseModel):
    detectedAt: IsoDatetimeOut
    kind: str
    target: str
    field: str
    expected: str
    observed: str


class MutationDrift(BaseModel):
    """Mutation drift telemetry.

    A drift event fires when a northbound mutation cleared through the
    config channel (pending-applied on GET /config) but the telemetry
    kept reporting the pre-mutation value past the grace window — the
    signal for a silent-reject class of bug. `driftCount` is monotonic
    for the process lifetime; `recentEvents` is a bounded ring, oldest
    first, last entry is the most recent.
    """

    driftCount: Annotated[int, Field(ge=0)]
    armedIntents: Annotated[int, Field(ge=0)]
    lastDriftAt: IsoDatetimeOut | None = None
    graceSeconds: Annotated[int, Field(ge=1)]
    recentEvents: list[MutationDriftEvent]


class StateStoreHealth(BaseModel):
    status: Literal["healthy", "degraded"]
    zonesTracked: Annotated[int, Field(ge=0)]
    pendingPushes: Annotated[int, Field(ge=0)]
    oldestPendingPushAgeSeconds: Annotated[int, Field(ge=0)] | None = None
    mutationDrift: MutationDrift


class ApiHealth(BaseModel):
    status: Literal["healthy"]
    uptimeSeconds: Annotated[int, Field(ge=0)]
    activeSseSubscribers: Annotated[int, Field(ge=0)]


class HealthComponents(BaseModel):
    thermostat: ThermostatHealth
    carrierCloud: CarrierCloudHealth
    stateStore: StateStoreHealth
    api: ApiHealth


class Version(BaseModel):
    proxy: str
    api: str
    commit: str
    builtAt: IsoDatetimeOut


class Health(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: IsoDatetimeOut
    components: HealthComponents
    version: Version


# ── Runtime config ───────────────────────────────────────────────────

class RuntimeConfig(BaseModel):
    passReqsIntervalSeconds: Annotated[int, Field(ge=10, le=3600)]
    logLevel: Literal["debug", "info", "warning", "error"]


# ── Energy ─────────────────────────────────────────────────────────────
# Thermostat POSTs `/systems/{serial}/energy` with the runtime data the
# MyInfinity app uses for its energy dashboard: SEER/HSPF efficiency
# ratings, per-mode display/enabled flags, and per-period (today,
# yesterday, this/last month, this/last year) hour counters per mode.

EnergyModeName = Literal[
    "cooling", "hpheat", "eheat", "gas", "reheat", "fangas", "fan", "looppump",
]

EnergyPeriodId = Literal[
    "day1", "day2", "month1", "month2", "year1", "year2",
]


class EnergyModeFlags(BaseModel):
    """display = whether the mode shows on the thermostat UI;
    enabled  = whether the mode is licensed/configured for this install.
    Both come from the thermostat's <{mode} display="..." enabled="..."/>
    elements with no inner text."""
    display: bool
    enabled: bool


class EnergyPeriod(BaseModel):
    """Per-period runtime hours, keyed by mode. Field names mirror the
    EnergyModeName enum so consumers can index by the same string."""
    id: EnergyPeriodId
    cooling: Annotated[int, Field(ge=0)] = 0
    hpheat: Annotated[int, Field(ge=0)] = 0
    eheat: Annotated[int, Field(ge=0)] = 0
    gas: Annotated[int, Field(ge=0)] = 0
    reheat: Annotated[int, Field(ge=0)] = 0
    fangas: Annotated[int, Field(ge=0)] = 0
    fan: Annotated[int, Field(ge=0)] = 0
    looppump: Annotated[int, Field(ge=0)] = 0


class Energy(BaseModel):
    """Parsed `<energy>` snapshot. Static config (efficiency ratings,
    per-mode flags) and rolling per-period runtime counters. Surfaces
    on `GET /v1/system/energy`."""
    seer: float | None = None
    hspf: float | None = None
    modes: dict[EnergyModeName, EnergyModeFlags]
    usage: list[EnergyPeriod]


# ── Equipment events (fault history) ──────────────────────────────────
# Thermostat POSTs `/systems/{serial}/equipment_events` carrying its
# fault-history list. Each entry is one observed fault code with
# source / description / first-occurrence timestamp / count / active
# flag (whether the fault is currently asserted).

class EquipmentEvent(BaseModel):
    id: str
    code: str
    source: str        # e.g. "ZN1", "IDU", "ODU"
    description: str
    localTime: str     # thermostat-local wall-clock; `YYYY-MM-DDTHH:MM:SS`
    occurrences: Annotated[int, Field(ge=0)]
    active: bool


class EquipmentEvents(BaseModel):
    events: list[EquipmentEvent]


# ── Outdoor / indoor unit live status ─────────────────────────────────
# Thermostat POSTs `/systems/{serial}/odu_status` and `/idu_status`
# carrying the live runtime state of the outdoor and indoor units —
# compressor stage + RPM, refrigerant pressures, blower RPM, static
# pressure, etc. Fields are populated only when the unit is running;
# off-state fields arrive as `na` / `invalid` / empty elements which
# the parser coerces to None.

class OduStatus(BaseModel):
    """Outdoor-unit live status snapshot.

    Every numeric field is `int | None` or `float | None` because the
    thermostat sends `na` / `invalid` literals when the corresponding
    sensor isn't reporting (typically because the unit is idle). The
    raw `opstat` string is preserved alongside the parsed integer
    `operatingStage` so consumers can introspect both.
    """
    odutype: str                                  # e.g. "hp2stgnoncomm"
    opstat: str                                   # raw, e.g. "Stage 0" / "off" / "Stage 2"
    operatingStage: int | None = None             # parsed N from "Stage N"; None for "off"/unknown
    opmode: str                                   # operating mode (off / cooling / hpheat / ...)
    outdoorTemperature: int | None = None         # <oat>, °F
    blowerRpm: int | None = None                  # <blwrpm>
    iduCfm: int | None = None                     # <iducfm>, indoor airflow CFM
    coilTemperature: int | None = None            # <oducoiltmp>
    leavingAirTemperature: int | None = None      # <lat>
    lineVoltage: int | None = None                # <linevolt>
    lockoutActive: bool = False                   # <lockactive>
    lockoutTime: int | None = None                # <locktime>, seconds (0 when not locked)
    compressorRpm: int | None = None              # <comprpm>
    suctionPressure: float | None = None          # <suctpress>, PSI
    suctionTemperature: int | None = None         # <sucttemp>
    suctionSuperheat: float | None = None         # <suctsupheat>
    dischargeTemperature: int | None = None       # <dischargetmp>
    spareSensorStatus: str | None = None          # <sparesensorstatus>
    spareSensorValue: float | None = None         # <sparesensorvalue>
    expansionValvePosition: int | None = None     # <exvpos>
    curtailActive: bool = False                   # <curtail>
    staticPressure: float | None = None           # <statpress>
    enteringRefrigerantTemperature: float | None = None  # <enterreftmp>
    # Stage availability — empty elements when not running.
    availMinHeatStage: int | None = None
    availMaxHeatStage: int | None = None
    availMinCoolStage: int | None = None
    availMaxCoolStage: int | None = None
    opMinHeatStage: int | None = None
    opMaxHeatStage: int | None = None
    opMinCoolStage: int | None = None
    opMaxCoolStage: int | None = None


class IduStatus(BaseModel):
    """Indoor-unit live status snapshot — fancoil / furnace / etc."""
    idutype: str                                  # e.g. "fancoilelectric"
    pwmBlower: bool = False                       # <pwmblower>
    opstat: str                                   # raw, e.g. "off" / "Stage 1"
    operatingStage: int | None = None
    iduCfm: int | None = None                     # <iducfm>
    blowerRpm: int | None = None                  # <blwrpm>
    staticPressure: float | None = None           # <statpress>
    coilTemperature: int | None = None            # <coiltemp>
    inducerRpm: int | None = None                 # <inducerrpm>, gas-furnace inducer
    leavingAirTemperature: int | None = None      # <lat>
    lockoutActive: bool = False                   # <lockoutactive>
    lockoutTime: str | None = None                # <lockouttime> — string ("off" / N seconds)
