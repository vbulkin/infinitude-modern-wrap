"""Pydantic v2 models for the Infinitude Modern Proxy API.

Source of truth for the wire format is design/openapi.yaml. These models must
stay in sync; a Phase 3 contract test will assert the FastAPI-generated
OpenAPI matches the hand-authored spec.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


# ── Scalar / enum types ──────────────────────────────────────────────

class HvacMode(str, Enum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    AUTO = "auto"
    FAN_ONLY = "fanonly"


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
PercentInt = Annotated[int, Field(ge=0, le=100)]
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
    until: datetime | None = None


class WholeHouseHold(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    active: bool
    activity: SystemHoldActivity | None = None
    until: datetime | None = None


class ZoneHoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    activity: ActivityId
    until: datetime | None = None


class WholeHouseHoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    activity: SystemHoldActivity
    until: datetime | None = None


# ── System / zones / activities / schedule ───────────────────────────

class System(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    mode: HvacMode
    outdoorTemperature: int
    humidifierOn: bool
    lastReportAt: datetime
    operatingStatusMessage: str
    serial: str
    hold: WholeHouseHold


class SystemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    mode: HvacMode | None = None


class Zone(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: ZoneIdStr
    name: str
    enabled: bool
    temperature: int
    humidity: PercentInt
    heatSetpoint: Temperature
    coolSetpoint: Temperature
    fan: FanSpeed
    damperPercent: PercentInt
    conditioning: HvacAction
    currentActivity: ActivityId
    hold: ZoneHold


class ZonePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heat: Temperature | None = None
    cool: Temperature | None = None
    activateHold: bool = True


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


# ── State + events ───────────────────────────────────────────────────

class State(BaseModel):
    system: System
    zones: list[Zone]
    lastUpdated: datetime


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
    until: datetime | None = None


# ── Health ───────────────────────────────────────────────────────────

class ThermostatHealth(BaseModel):
    status: Literal["healthy", "stale", "unreachable"]
    lastContact: datetime | None = None
    lastContactAgeSeconds: Annotated[int, Field(ge=0)] | None = None
    expectedIntervalSeconds: Annotated[int, Field(ge=1)]
    staleThresholdSeconds: Annotated[int, Field(ge=1)]


class CarrierCloudHealth(BaseModel):
    status: Literal["healthy", "degraded", "unreachable", "disabled"]
    lastSuccess: datetime | None = None
    lastAttempt: datetime | None = None
    lastError: str | None = None
    passReqsIntervalSeconds: Annotated[int, Field(ge=10, le=3600)]
    consecutiveFailures: Annotated[int, Field(ge=0)]


class StateStoreHealth(BaseModel):
    status: Literal["healthy", "degraded"]
    zonesTracked: Annotated[int, Field(ge=0)]
    pendingPushes: Annotated[int, Field(ge=0)]
    oldestPendingPushAgeSeconds: Annotated[int, Field(ge=0)] | None = None


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
    builtAt: datetime


class Health(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime
    components: HealthComponents
    version: Version


# ── Runtime config ───────────────────────────────────────────────────

class RuntimeConfig(BaseModel):
    passReqsIntervalSeconds: Annotated[int, Field(ge=10, le=3600)]
    logLevel: Literal["debug", "info", "warning", "error"]
