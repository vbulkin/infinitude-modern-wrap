"""FastAPI app — northbound API for the Infinitude Modern Proxy.

Phase 2 scaffold: /v1/healthz, /v1/version, /v1/state, /v1/config.
Phase 3.1 adds the southbound telemetry handler — /v1/state now
overlays the latest telemetry snapshot onto the canned defaults so
fields the thermostat has reported become live.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from . import __version__
from .canned_state import canned_state
from .models import (
    Activity,
    ActivityId,
    ApiHealth,
    CarrierCloudHealth,
    FanSpeed,
    Health,
    HealthComponents,
    HumidityConfig,
    HvacAction,
    HvacMode,
    IduConfig,
    NotificationBody,
    NotificationChangeEntry,
    NotificationEnvelope,
    OduConfig,
    RuntimeConfig,
    Schedule,
    State,
    StateStoreHealth,
    System,
    ThermostatHealth,
    VacationConfig,
    Version,
    Zone,
    ZoneHold,
)
from .persistence import Persistence
from .settings import load_settings
from .southbound import create_southbound_router
from .state_store import StateStore, StoredConfig, StoredNotification, StoredTelemetry

logger = logging.getLogger(__name__)

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
    # When the caller supplies a store (tests), we trust it's pre-configured
    # and skip the auto-open lifespan path. Production entrypoint calls
    # create_app() with no args → lifespan opens the DB at settings.db_path.
    owns_store = store is None
    store = store or StateStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        persistence: Persistence | None = None
        if owns_store:
            try:
                persistence = await Persistence.open(settings.db_path)
                store.attach_persistence(persistence)
                await store.restore_from_persistence()
            except Exception:
                # A broken/locked DB shouldn't brick the proxy — degrade
                # to in-memory-only mode and log. Operator can delete the
                # file and restart to recover.
                logger.exception(
                    "persistence: failed to open %s; running in-memory only",
                    settings.db_path,
                )
                persistence = None
                store.attach_persistence(None)
        try:
            yield
        finally:
            if persistence is not None:
                await persistence.close()

    app = FastAPI(
        title="Infinitude Modern Proxy API",
        version=__version__,
        description="Northbound HTTP API for the modernized Infinitude proxy.",
        lifespan=lifespan,
    )
    app.include_router(create_southbound_router(store))

    @app.get("/v1/healthz", response_model=Health, tags=["health"])
    async def get_health() -> Health:
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
        pending_count = 0
        oldest_age: int | None = None
        if store.persistence is not None:
            pending_count = await store.persistence.unapplied_count()
            raw_age = await store.persistence.oldest_pending_age_seconds()
            oldest_age = int(raw_age) if raw_age is not None else None
        zones_tracked = len(store.get_config().config.zones) if store.get_config() else 0
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
                    zonesTracked=zones_tracked,
                    pendingPushes=pending_count,
                    oldestPendingPushAgeSeconds=oldest_age,
                ),
                api=ApiHealth(
                    status="healthy",
                    uptimeSeconds=_uptime_seconds(),
                    activeSseSubscribers=store.subscriber_count,
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

    @app.get(
        "/v1/zones/{zone_id}/activities",
        response_model=list[Activity],
        tags=["zones"],
    )
    def get_zone_activities(zone_id: str) -> list[Activity]:
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        for zc in stored.config.zones:
            if zc.id == zone_id:
                return [Activity.model_validate(a) for a in zc.activities]
        raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")

    @app.get(
        "/v1/zones/{zone_id}/schedule",
        response_model=Schedule,
        tags=["zones"],
    )
    def get_zone_schedule(zone_id: str) -> Schedule:
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        for zc in stored.config.zones:
            if zc.id == zone_id:
                return Schedule(zoneId=zone_id, days=list(zc.schedule))
        raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")

    @app.get(
        "/v1/system/vacation", response_model=VacationConfig, tags=["system"]
    )
    def get_vacation() -> VacationConfig:
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return VacationConfig.model_validate(stored.config.vacation)

    @app.get(
        "/v1/system/humidity", response_model=HumidityConfig, tags=["system"]
    )
    def get_humidity() -> HumidityConfig:
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return HumidityConfig.model_validate(stored.config.humidity)

    @app.get("/v1/system/idu", response_model=IduConfig, tags=["system"])
    def get_idu() -> IduConfig:
        stored = store.get_idu()
        if stored is None:
            raise HTTPException(
                status_code=404, detail="no idu_config received yet"
            )
        return stored.config

    @app.get("/v1/system/odu", response_model=OduConfig, tags=["system"])
    def get_odu() -> OduConfig:
        stored = store.get_odu()
        if stored is None:
            raise HTTPException(
                status_code=404, detail="no odu_config received yet"
            )
        return stored.config

    @app.get(
        "/v1/notifications",
        response_model=list[NotificationEnvelope],
        tags=["events"],
    )
    def get_notifications(
        since: datetime | None = Query(
            None,
            description=(
                "ISO-8601 timestamp — return only notifications whose "
                "receivedAt is strictly greater. Intended cursor for "
                "SSE reconnect backfill; use the receivedAt of the last "
                "event the client processed."
            ),
        ),
        limit: int = Query(50, ge=1, le=50),
    ) -> list[NotificationEnvelope]:
        """Recent-notifications ring-buffer view for SSE reconnect backfill.

        Oldest-first so clients can replay in arrival order. The ring
        buffer holds up to 50 entries — if `since` is older than the
        buffer's oldest event the caller has missed events and this
        endpoint can't prove it; a future slice may add a truncation
        header or a `gap` response field if that becomes operationally
        important.
        """
        stored = store.recent_notifications()
        if since is not None:
            stored = [sn for sn in stored if sn.receivedAt > since]
        stored = stored[-limit:]
        return [_envelope_from_stored(sn) for sn in stored]

    @app.get("/v1/events", tags=["events"])
    async def stream_events(request: Request) -> EventSourceResponse:
        """SSE stream of thermostat notifications.

        Each event is a single StoredNotification as JSON. Clients
        reconnect on disconnect; we don't replay backfill on this slice —
        /v1/notifications (REST) is the catch-up surface when we add it.
        The 15s keepalive is well under typical proxy/idle-connection
        timeouts and doubles as the disconnect-detection tick.
        """
        queue = store.subscribe()

        async def event_gen():
            try:
                while True:
                    if await request.is_disconnected():
                        return
                    try:
                        sn = await asyncio.wait_for(queue.get(), timeout=15.0)
                    except asyncio.TimeoutError:
                        yield {"event": "keepalive", "data": ""}
                        continue
                    yield {
                        "event": "notification",
                        "data": _stored_notification_json(sn),
                    }
            finally:
                store.unsubscribe(queue)

        return EventSourceResponse(event_gen())

    return app


def _envelope_from_stored(sn: StoredNotification) -> NotificationEnvelope:
    """Lift a StoredNotification dataclass into the northbound envelope.

    Single serialization shape for both SSE frames and the /v1/
    notifications backfill endpoint — if the wire format ever changes
    (additional metadata, rename, etc.) this is the one place to edit.
    """
    return NotificationEnvelope(
        serial=sn.serial,
        receivedAt=sn.receivedAt,
        event=NotificationBody(
            type=sn.event.type,
            code=sn.event.code,
            message=sn.event.message,
            timestamp=sn.event.timestamp,
            changes=[
                NotificationChangeEntry(id=c.id, zone=c.zone)
                for c in sn.event.changes
            ],
        ),
    )


def _stored_notification_json(sn: StoredNotification) -> str:
    """Serialize a StoredNotification for SSE payload.

    Routes through _envelope_from_stored so SSE frames and backfill
    responses are guaranteed to have identical shape.
    """
    return _envelope_from_stored(sn).model_dump_json()


app = create_app()
