"""FastAPI app — northbound API for the Infinitude Modern Proxy.

Phase 2 scaffold: /v1/healthz, /v1/version, /v1/state, /v1/config.
Phase 3.1 adds the southbound telemetry handler — /v1/state now
overlays the latest telemetry snapshot onto the canned defaults so
fields the thermostat has reported become live.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import FastAPI

from . import __version__
from .canned_state import canned_state
from .models import (
    ActivityId,
    ApiHealth,
    CarrierCloudHealth,
    FanSpeed,
    Health,
    HealthComponents,
    HvacAction,
    RuntimeConfig,
    State,
    StateStoreHealth,
    System,
    ThermostatHealth,
    Version,
    Zone,
    ZoneHold,
)
from .settings import load_settings
from .southbound import create_southbound_router
from .state_store import StateStore, StoredTelemetry

_STARTUP_MONOTONIC = time.monotonic()


def _uptime_seconds() -> int:
    return int(time.monotonic() - _STARTUP_MONOTONIC)


def _overlay_telemetry(base: State, stored: StoredTelemetry) -> State:
    snap = stored.snapshot
    telemetry_zones = {z.id: z for z in snap.zones}
    zones = [
        Zone(
            id=z.id,
            name=tz.name if (tz := telemetry_zones.get(z.id)) else z.name,
            enabled=tz.enabled if tz else z.enabled,
            temperature=tz.temperature if tz else z.temperature,
            humidity=tz.humidity if tz else z.humidity,
            heatSetpoint=tz.heatSetpoint if tz else z.heatSetpoint,
            coolSetpoint=tz.coolSetpoint if tz else z.coolSetpoint,
            fan=FanSpeed(tz.fan) if tz else z.fan,
            damperPercent=tz.damperPercent if tz else z.damperPercent,
            conditioning=HvacAction(tz.conditioning) if tz else z.conditioning,
            currentActivity=ActivityId(tz.currentActivity) if tz else z.currentActivity,
            hold=ZoneHold(active=tz.holdActive) if tz else z.hold,
        )
        for z in base.zones
    ]
    return State(
        lastUpdated=stored.receivedAt,
        system=System(
            mode=base.system.mode,
            outdoorTemperature=snap.outdoorTemperature,
            humidifierOn=snap.humidifierOn,
            lastReportAt=snap.localTime,
            operatingStatusMessage=snap.operatingStatusMessage,
            serial=stored.serial,
            hold=base.system.hold,
        ),
        zones=zones,
    )


def create_app(store: StateStore | None = None) -> FastAPI:
    settings = load_settings()
    store = store or StateStore()
    app = FastAPI(
        title="Infinitude Modern Proxy API",
        version=__version__,
        description="Northbound HTTP API for the modernized Infinitude proxy.",
    )
    app.include_router(create_southbound_router(store))

    @app.get("/v1/healthz", response_model=Health, tags=["health"])
    def get_health() -> Health:
        now = datetime.now(timezone.utc)
        stored = store.get_telemetry()
        if stored is None:
            thermostat = ThermostatHealth(
                status="unreachable",
                lastContact=None,
                lastContactAgeSeconds=None,
                expectedIntervalSeconds=90,
                staleThresholdSeconds=300,
            )
            overall: str = "degraded"
        else:
            age = int((now - stored.receivedAt).total_seconds())
            thermostat = ThermostatHealth(
                status="healthy" if age < 300 else "stale",
                lastContact=stored.receivedAt,
                lastContactAgeSeconds=age,
                expectedIntervalSeconds=90,
                staleThresholdSeconds=300,
            )
            overall = "healthy" if age < 300 else "degraded"
        return Health(
            status=overall,  # type: ignore[arg-type]
            timestamp=now,
            components=HealthComponents(
                thermostat=thermostat,
                carrierCloud=CarrierCloudHealth(
                    status="disabled",
                    lastSuccess=None,
                    lastAttempt=None,
                    lastError=None,
                    passReqsIntervalSeconds=settings.pass_reqs,
                    consecutiveFailures=0,
                ),
                stateStore=StateStoreHealth(
                    status="healthy",
                    zonesTracked=0,
                    pendingPushes=0,
                    oldestPendingPushAgeSeconds=None,
                ),
                api=ApiHealth(
                    status="healthy",
                    uptimeSeconds=_uptime_seconds(),
                    activeSseSubscribers=0,
                ),
            ),
            version=Version(
                proxy=__version__,
                api="v1",
                commit=settings.commit_sha,
                builtAt=datetime.fromisoformat(
                    settings.built_at.replace("Z", "+00:00")
                ),
            ),
        )

    @app.get("/v1/version", response_model=Version, tags=["meta"])
    def get_version() -> Version:
        return Version(
            proxy=__version__,
            api="v1",
            commit=settings.commit_sha,
            builtAt=datetime.fromisoformat(
                settings.built_at.replace("Z", "+00:00")
            ),
        )

    @app.get("/v1/config", response_model=RuntimeConfig, tags=["meta"])
    def get_config() -> RuntimeConfig:
        return RuntimeConfig(
            passReqsIntervalSeconds=settings.pass_reqs,
            logLevel=settings.log_level,  # type: ignore[arg-type]
        )

    @app.get("/v1/state", response_model=State, tags=["state"])
    def get_state() -> State:
        base = canned_state()
        stored = store.get_telemetry()
        return _overlay_telemetry(base, stored) if stored else base

    return app


app = create_app()
