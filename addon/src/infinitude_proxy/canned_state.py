"""Canned state for Phase 2.

Returned by /v1/state until the southbound handler (Phase 3) begins
writing real thermostat telemetry to the state store. The shape MUST
match the Pydantic models so tests exercise the real validation path.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    ActivityId,
    FanSpeed,
    HvacAction,
    HvacMode,
    State,
    System,
    WholeHouseHold,
    Zone,
    ZoneHold,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def canned_state() -> State:
    now = _now()
    return State(
        lastUpdated=now,
        system=System(
            mode=HvacMode.COOL,
            outdoorTemperature=78,
            humidifierOn=False,
            lastReportAt=now,
            operatingStatusMessage="idle",
            serial="0000DEMO0000",
            hold=WholeHouseHold(active=False),
        ),
        zones=[
            Zone(
                id="1",
                name="Main Floor",
                enabled=True,
                temperature=72,
                humidity=45,
                heatSetpoint=68,
                coolSetpoint=76,
                fan=FanSpeed.OFF,
                damperPercent=100,
                conditioning=HvacAction.IDLE,
                currentActivity=ActivityId.HOME,
                hold=ZoneHold(active=False),
            ),
            Zone(
                id="2",
                name="Upstairs",
                enabled=True,
                temperature=74,
                humidity=47,
                heatSetpoint=66,
                coolSetpoint=75,
                fan=FanSpeed.OFF,
                damperPercent=67,
                conditioning=HvacAction.COOLING,
                currentActivity=ActivityId.HOME,
                hold=ZoneHold(active=False),
            ),
        ],
    )
