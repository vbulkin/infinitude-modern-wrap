"""FastAPI app — northbound API for the Infinitude Modern Proxy.

Phase 2 scaffold: /v1/healthz, /v1/version, /v1/state, /v1/config.
Phase 3.1 adds the southbound telemetry handler — /v1/state now
overlays the latest telemetry snapshot onto the canned defaults so
fields the thermostat has reported become live.
"""

from __future__ import annotations

import logging
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
    HvacMode,
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
from .state_store import StateStore, StoredConfig, StoredTelemetry

_STARTUP_MONOTONIC = time.monotonic()


def _uptime_seconds() -> int:
    return int(time.monotonic() - _STARTUP_MONOTONIC)


def _configure_logging(level: str) -> None:
    """Configure the infinitude_proxy.* logger tree.

    Scoped so uvicorn's own access/error loggers keep their config.
    Idempotent — tests that spin up multiple app instances won't stack
    handlers. Policy: see design/LOGGING.md.
    """
    proxy_logger = logging.getLogger("infinitude_proxy")
    proxy_logger.setLevel(level.upper())
    if not any(isinstance(h, logging.StreamHandler) for h in proxy_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        proxy_logger.addHandler(handler)
    proxy_logger.propagate = False


def _compose_state(
    stored_config: StoredConfig | None,
    stored_telemetry: StoredTelemetry | None,
) -> State:
    """Assemble /v1/state from the latest config + telemetry snapshots.

    Config sets the skeleton (mode, hold, zone identity). Telemetry
    fills the live values. If neither has landed we fall back to the
    canned demo state so the endpoint stays useful on a cold start.
    """
    if stored_config is None and stored_telemetry is None:
        return canned_state()

    base = canned_state()
    telemetry_zones = (
        {z.id: z for z in stored_telemetry.snapshot.zones}
        if stored_telemetry else {}
    )

    if stored_config is not None:
        cfg = stored_config.config
        serial = stored_config.serial
        zone_skeletons = [(zc.id, zc.name, zc.enabled, zc.hold) for zc in cfg.zones]
        system_mode = HvacMode(cfg.mode)
        whole_hold = cfg.wholeHouseHold
    else:
        serial = stored_telemetry.serial if stored_telemetry else base.system.serial
        zone_skeletons = [(z.id, z.name, z.enabled, z.hold) for z in base.zones]
        system_mode = base.system.mode
        whole_hold = base.system.hold

    base_zone_by_id = {z.id: z for z in base.zones}
    zones: list[Zone] = []
    for zid, zname, zenabled, zhold in zone_skeletons:
        tz = telemetry_zones.get(zid)
        b = base_zone_by_id.get(zid)
        zones.append(
            Zone(
                id=zid,
                name=zname,
                enabled=zenabled,
                temperature=tz.temperature if tz else (b.temperature if b else 70),
                humidity=tz.humidity if tz else (b.humidity if b else 50),
                heatSetpoint=tz.heatSetpoint if tz else (b.heatSetpoint if b else 68),
                coolSetpoint=tz.coolSetpoint if tz else (b.coolSetpoint if b else 76),
                fan=FanSpeed(tz.fan) if tz else (b.fan if b else FanSpeed.OFF),
                damperPercent=tz.damperPercent if tz else (b.damperPercent if b else 100),
                conditioning=HvacAction(tz.conditioning) if tz else (b.conditioning if b else HvacAction.IDLE),
                currentActivity=ActivityId(tz.currentActivity) if tz else (b.currentActivity if b else ActivityId.HOME),
                hold=ZoneHold(active=tz.holdActive) if tz else zhold,
            )
        )

    if stored_telemetry is not None:
        snap = stored_telemetry.snapshot
        system = System(
            mode=system_mode,
            outdoorTemperature=snap.outdoorTemperature,
            humidifierOn=snap.humidifierOn,
            lastReportAt=snap.localTime,
            operatingStatusMessage=snap.operatingStatusMessage,
            serial=serial,
            hold=whole_hold,
        )
        last_updated = stored_telemetry.receivedAt
    else:
        assert stored_config is not None
        system = System(
            mode=system_mode,
            outdoorTemperature=base.system.outdoorTemperature,
            humidifierOn=base.system.humidifierOn,
            lastReportAt=stored_config.receivedAt,
            operatingStatusMessage=base.system.operatingStatusMessage,
            serial=serial,
            hold=whole_hold,
        )
        last_updated = stored_config.receivedAt

    return State(lastUpdated=last_updated, system=system, zones=zones)


def create_app(store: StateStore | None = None) -> FastAPI:
    settings = load_settings()
    _configure_logging(settings.log_level)
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
        return _compose_state(store.get_config(), store.get_telemetry())

    return app


app = create_app()
