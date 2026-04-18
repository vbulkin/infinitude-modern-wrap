"""FastAPI app — northbound API for the Infinitude Modern Proxy.

Phase 2 scaffold: /v1/healthz, /v1/version, /v1/state, /v1/config.
Southbound protocol and mutating endpoints land in later phases.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import FastAPI

from . import __version__
from .canned_state import canned_state
from .models import (
    ApiHealth,
    CarrierCloudHealth,
    Health,
    HealthComponents,
    RuntimeConfig,
    State,
    StateStoreHealth,
    ThermostatHealth,
    Version,
)
from .settings import load_settings

_STARTUP_MONOTONIC = time.monotonic()


def _uptime_seconds() -> int:
    return int(time.monotonic() - _STARTUP_MONOTONIC)


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="Infinitude Modern Proxy API",
        version=__version__,
        description="Northbound HTTP API for the modernized Infinitude proxy.",
    )

    @app.get("/v1/healthz", response_model=Health, tags=["health"])
    def get_health() -> Health:
        now = datetime.now(timezone.utc)
        return Health(
            status="degraded",
            timestamp=now,
            components=HealthComponents(
                thermostat=ThermostatHealth(
                    status="unreachable",
                    lastContact=None,
                    lastContactAgeSeconds=None,
                    expectedIntervalSeconds=90,
                    staleThresholdSeconds=300,
                ),
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
        return canned_state()

    return app


app = create_app()
