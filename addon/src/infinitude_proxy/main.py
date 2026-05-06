"""FastAPI app — northbound API for the Infinitude Modern Proxy.

Phase 2 scaffold: /v1/healthz, /v1/version, /v1/state, /v1/config.
Phase 3.1 adds the southbound telemetry handler — /v1/state now
overlays the latest telemetry snapshot onto the canned defaults so
fields the thermostat has reported become live.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, Response
from sse_starlette.sse import EventSourceResponse

from . import __version__
from .models import (
    Activity,
    ActivityId,
    ActivityPatch,
    ApiHealth,
    CarrierCloudHealth,
    FanSpeed,
    Health,
    HealthComponents,
    HumidityConfig,
    HumidityPatch,
    HvacAction,
    HvacMode,
    IduConfig,
    FilterReminder,
    MutationDrift,
    MutationDriftEvent,
    NotificationBody,
    NotificationChangeEntry,
    NotificationEnvelope,
    OduConfig,
    RuntimeConfig,
    Schedule,
    SchedulePut,
    StrictIsoDatetime,
    ServiceReminderItem,
    ServiceReminders,
    State,
    StateStoreHealth,
    System,
    SystemPatch,
    ThermostatHealth,
    VacationConfig,
    VacationPatch,
    Version,
    WholeHouseHoldRequest,
    Zone,
    ZoneHold,
    ZoneHoldRequest,
    ZonePatch,
)
from .capture import CaptureControl, CaptureMiddleware
from .carrier_bridge import CarrierBridge
from .debug_api import create_debug_router
from .errors import register_error_handlers
from .forward_proxy import ForwardProxy, extract_target_url
from .mutations import (
    apply_activity_set,
    apply_humidity_set,
    apply_schedule_set,
    apply_system_hold_clear,
    apply_system_hold_set,
    apply_system_mode_set,
    apply_vacation_set,
    apply_zone_hold_clear,
    apply_zone_hold_set,
    apply_zone_setpoints_set,
    snap_quarter_hour,
)
from .persistence import Persistence
from .settings import load_settings
from .southbound import create_southbound_router
from .state_store import StateStore, StoredConfig, StoredNotification, StoredTelemetry

logger = logging.getLogger(__name__)

_STARTUP_MONOTONIC = time.monotonic()


def _uptime_seconds() -> int:
    return int(time.monotonic() - _STARTUP_MONOTONIC)


def _reject_unknown_query(request: Request, allowed: set[str]) -> None:
    """Reject any query parameter whose name isn't in `allowed`.

    FastAPI silently drops unknown query params by default; schemathesis's
    coverage generator probes for that (sending e.g.
    `x-schemathesis-unknown-property=42`) and fails the run when it
    succeeds. Endpoints that take tightly-scoped query params call this
    to match the spec's `additionalProperties: false`-equivalent stance.
    """
    unknown = [k for k in request.query_params.keys() if k not in allowed]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown query parameter(s): {', '.join(sorted(unknown))}",
        )


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


def _build_zone(zc, tz) -> Zone:
    """Merge a config-side ZoneConfig and (optional) telemetry zone into
    the Zone wire shape.

    Single source of truth for both `/v1/state` and per-zone mutation
    responses. Without this consolidation the two paths drifted — state
    showed telemetry-only setpoints (stale by one thermostat poll cycle
    after a write), while `_zone_response` correctly preferred the
    held-activity setpoints from config. The HA integration polls
    state, so the user saw temp bumps revert until the thermostat
    caught up.

    Hold semantics:
      * `active` — telemetry's `holdActive` bool when present, else the
        config-side flag (only stale on a fresh-write race window).
      * `activity` / `until` — config-side; telemetry doesn't carry them.

    Setpoints + fan:
      * If the zone is in a hold and the held activity is in config,
        read heat/cool/fan from that activity. This is what the
        thermostat will display once it pulls the pending write, so
        the API echoes user intent immediately.
      * Otherwise fall back to telemetry's last-reported values.
    """
    hold_heat: int | None = None
    hold_cool: int | None = None
    hold_fan: str | None = None
    if zc.hold.active and zc.hold.activity:
        held = next(
            (a for a in zc.activities if a.id == zc.hold.activity),
            None,
        )
        if held is not None:
            hold_heat = held.heat
            hold_cool = held.cool
            hold_fan = held.fan
    return Zone(
        id=zc.id,
        name=zc.name,
        enabled=zc.enabled,
        temperature=tz.temperature if tz else None,
        humidity=tz.humidity if tz else None,
        heatSetpoint=(
            hold_heat if hold_heat is not None
            else (tz.heatSetpoint if tz else None)
        ),
        coolSetpoint=(
            hold_cool if hold_cool is not None
            else (tz.coolSetpoint if tz else None)
        ),
        fan=(
            FanSpeed(hold_fan) if hold_fan is not None
            else (FanSpeed(tz.fan) if tz else None)
        ),
        damperPercent=tz.damperPercent if tz else None,
        conditioning=HvacAction(tz.conditioning) if tz else None,
        currentActivity=(
            ActivityId(zc.hold.activity)
            if zc.hold.active and zc.hold.activity
            else (ActivityId(tz.currentActivity) if tz else None)
        ),
        hold=ZoneHold(
            active=tz.holdActive if tz else zc.hold.active,
            activity=zc.hold.activity,
            until=zc.hold.until,
        ),
    )


def _compose_state(
    stored_config: StoredConfig | None,
    stored_telemetry: StoredTelemetry | None,
) -> State:
    """Assemble /v1/state from the latest config + telemetry snapshots.

    Config is authoritative for the skeleton (zone identity, mode, hold).
    Telemetry fills live fields (temperatures, fan, conditioning). Until
    config has landed, there is nothing truthful to return — callers
    raise 503 on a None result.
    """
    if stored_config is None:
        raise HTTPException(
            status_code=503,
            detail="Thermostat has not reported yet",
        )

    cfg = stored_config.config
    serial = stored_config.serial
    telemetry_zones = (
        {z.id: z for z in stored_telemetry.snapshot.zones}
        if stored_telemetry else {}
    )

    zones: list[Zone] = [
        _build_zone(zc, telemetry_zones.get(zc.id)) for zc in cfg.zones
    ]

    if stored_telemetry is not None:
        snap = stored_telemetry.snapshot
        system = System(
            mode=HvacMode(cfg.mode),
            outdoorTemperature=snap.outdoorTemperature,
            humidifierOn=snap.humidifierOn,
            lastReportAt=snap.localTime,
            operatingStatusMessage=snap.operatingStatusMessage,
            serial=serial,
            hold=cfg.wholeHouseHold,
        )
        last_updated = stored_telemetry.receivedAt
    else:
        system = System(
            mode=HvacMode(cfg.mode),
            serial=serial,
            hold=cfg.wholeHouseHold,
        )
        last_updated = stored_config.receivedAt

    return State(lastUpdated=last_updated, system=system, zones=zones)


def create_app(
    store: StateStore | None = None,
    *,
    capture_control: CaptureControl | None = None,
    forward_proxy: ForwardProxy | None = None,
    carrier_bridge: CarrierBridge | None = None,
) -> FastAPI:
    settings = load_settings()
    _configure_logging(settings.log_level)
    # When the caller supplies a store (tests), we trust it's pre-configured
    # and skip the auto-open lifespan path. Production entrypoint calls
    # create_app() with no args → lifespan opens the DB at settings.db_path.
    owns_store = store is None
    store = store or StateStore()
    # Single CaptureControl per app — holds the start/stop flag, max-rows
    # cap, and the persistence handle for the middleware to reach. Tests
    # can inject a pre-wired one (e.g., attached to a test persistence)
    # to exercise capture without running the lifespan path.
    control = capture_control if capture_control is not None else CaptureControl()
    # ForwardProxy is the thermostat → carrier.com relay. Lifespan opens/
    # closes the underlying httpx client; the catch-all route at the
    # bottom of this function dispatches matching requests to it. When
    # capture is on, the proxy emits `carrier_out` rows mirroring the
    # ASGI middleware's southbound/northbound output. Tests inject a
    # pre-wired instance with an httpx.MockTransport so they don't hit
    # the network.
    if forward_proxy is None:
        forward_proxy = ForwardProxy(capture_control=control)
    fproxy = forward_proxy
    # CarrierBridge is the implicit-relay path — mirrors thermostat
    # status posts up to Carrier (so MyInfinity sees fresh state) and
    # gates /systems/{id}/config on the carrier_changes window so
    # app-initiated changes flow back down. Defaults to enabled at
    # `pass_reqs` cadence; disable by passing a CarrierBridge with
    # pass_reqs=0 if you want offline-first behavior.
    if carrier_bridge is None:
        carrier_bridge = CarrierBridge(
            pass_reqs=settings.pass_reqs, capture_control=control,
        )
    cbridge = carrier_bridge

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        persistence: Persistence | None = None
        if owns_store:
            try:
                persistence = await Persistence.open(settings.db_path)
                store.attach_persistence(persistence)
                await store.restore_from_persistence()
                control.attach_persistence(persistence)
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
                control.attach_persistence(None)
        await fproxy.open()
        await cbridge.open()
        try:
            yield
        finally:
            # Detach before close so any in-flight capture task sees a
            # clean "no persistence" state rather than a closed handle.
            control.attach_persistence(None)
            await cbridge.close()
            await fproxy.close()
            if persistence is not None:
                await persistence.close()

    app = FastAPI(
        title="Infinitude Modern Proxy API",
        version=__version__,
        description="Northbound HTTP API for the modernized Infinitude proxy.",
        lifespan=lifespan,
        # Disable the built-in /docs handler so we can serve a Swagger UI
        # page with a *relative* openapi URL. Under HA Supervisor ingress
        # the addon is mounted at `/api/hassio_ingress/<token>/`, but
        # Swagger UI's default behavior is to fetch an absolute
        # `/openapi.json` from the host root — which 404s because that
        # path isn't proxied. A `./openapi.json` reference resolves
        # against the page URL and works under both ingress and direct
        # port access.
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="./openapi.json",
            title=f"{app.title} — docs",
        )

    # Middleware runs outside-in; installing capture last means it's the
    # innermost wrapper, closest to the app. That's what we want — it
    # needs to see the exact bytes the app receives and emits after all
    # other middleware (CORS, error handlers) have done their work.
    app.add_middleware(CaptureMiddleware, control=control)
    register_error_handlers(app)
    app.include_router(create_southbound_router(store, cbridge))
    app.include_router(create_debug_router(control))

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root_landing() -> str:
        return (
            "<!doctype html><html><head><title>Infinitude Modern Proxy</title>"
            "<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:40rem}"
            "h1{margin-bottom:0.25rem}.muted{color:#666}"
            "ul{line-height:1.8}code{background:#f2f2f2;padding:0.1rem 0.3rem;border-radius:3px}"
            "</style></head><body>"
            f"<h1>Infinitude Modern Proxy</h1>"
            f'<p class="muted">v{__version__} &middot; typed OpenAPI proxy for Carrier/Bryant Infinity thermostats.</p>'
            "<ul>"
            '<li><a href="v1/healthz">/v1/healthz</a> &mdash; health + thermostat last-contact</li>'
            '<li><a href="v1/state">/v1/state</a> &mdash; current composed state</li>'
            '<li><a href="docs">/docs</a> &mdash; Swagger UI</li>'
            '<li><a href="openapi.json">/openapi.json</a> &mdash; OpenAPI schema</li>'
            "</ul>"
            "</body></html>"
        )

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
        drift = store.drift
        drift_events = [
            MutationDriftEvent(
                detectedAt=ev.detected_at,
                kind=ev.kind,
                target=ev.target,
                field=ev.field,
                expected=str(ev.expected),
                observed=str(ev.observed),
            )
            for ev in drift.recent_events()
        ]
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
                    mutationDrift=MutationDrift(
                        driftCount=drift.drift_count,
                        armedIntents=drift.armed_count,
                        lastDriftAt=drift.last_drift_at,
                        graceSeconds=int(drift.grace.total_seconds()),
                        recentEvents=drift_events,
                    ),
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

    @app.get("/v1/zones", response_model=list[Zone], tags=["zones"])
    def list_zones() -> list[Zone]:
        """All zones (including disabled). Per openapi spec: disabled
        zones are included so clients can present the full unit layout —
        filtering is the client's call."""
        stored_config = store.get_config()
        if stored_config is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        telemetry = store.get_telemetry()
        return [
            _zone_response(stored_config, telemetry, zc.id)
            for zc in stored_config.config.zones
        ]

    @app.get("/v1/zones/{zone_id}", response_model=Zone, tags=["zones"])
    def get_zone(zone_id: str) -> Zone:
        stored_config = store.get_config()
        if stored_config is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        if not any(zc.id == zone_id for zc in stored_config.config.zones):
            raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")
        return _zone_response(stored_config, store.get_telemetry(), zone_id)

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
        "/v1/zones/{zone_id}/activities/{activity_id}",
        response_model=Activity,
        tags=["zones"],
    )
    def get_zone_activity(zone_id: str, activity_id: str) -> Activity:
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        zone_cfg = next(
            (zc for zc in stored.config.zones if zc.id == zone_id), None
        )
        if zone_cfg is None:
            raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")
        try:
            aid = ActivityId(activity_id)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"activity {activity_id} not found in zone {zone_id}",
            )
        match = next((a for a in zone_cfg.activities if a.id == aid.value), None)
        if match is None:
            raise HTTPException(
                status_code=404,
                detail=f"activity {activity_id} not found in zone {zone_id}",
            )
        return Activity.model_validate(match)

    @app.patch(
        "/v1/zones/{zone_id}/activities/{activity_id}",
        response_model=Activity,
        tags=["zones"],
    )
    async def patch_zone_activity(
        zone_id: str, activity_id: str, body: ActivityPatch
    ) -> Activity:
        """Edit an activity's setpoints and/or fan. Sparse update — only
        supplied fields are written. Unlike PATCH /v1/zones/{id} (which
        edits the `manual` activity and engages the hold), this endpoint
        edits whichever activity you name without touching hold state,
        so you can tweak the `home` or `sleep` profiles without forcing
        an immediate override.
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        zone_cfg = next(
            (zc for zc in stored.config.zones if zc.id == zone_id), None
        )
        if zone_cfg is None:
            raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")
        try:
            aid = ActivityId(activity_id)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"activity {activity_id} not found in zone {zone_id}",
            )
        if not any(a.id == aid.value for a in zone_cfg.activities):
            raise HTTPException(
                status_code=404,
                detail=f"activity {activity_id} not found in zone {zone_id}",
            )
        supplied = body.model_dump(exclude_none=True)
        if not supplied:
            raise HTTPException(
                status_code=422, detail="at least one field must be supplied"
            )
        payload = {"zone_id": zone_id, "activity_id": activity_id, **supplied}
        updated = await store.mutate_config(
            apply_activity_set,
            serial=stored.serial,
            kind="activity_set",
            target=f"zone:{zone_id}:activity:{activity_id}",
            payload=payload,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        updated_zone = next(
            zc for zc in updated.config.zones if zc.id == zone_id
        )
        updated_activity = next(
            a for a in updated_zone.activities if a.id == aid.value
        )
        return Activity.model_validate(updated_activity)

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

    @app.put(
        "/v1/zones/{zone_id}/schedule",
        response_model=Schedule,
        tags=["zones"],
    )
    async def put_zone_schedule(zone_id: str, body: SchedulePut) -> Schedule:
        """Overwrite a zone's 7-day schedule.

        PUT (not PATCH) because the body is the full program — all seven
        days, each with 1-5 periods. Duplicate or missing day names are
        rejected at 422 so a client bug doesn't silently drop a day.
        Period ids must be unique within a day for the same reason.
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        if not any(zc.id == zone_id for zc in stored.config.zones):
            raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")
        day_names = [d.day for d in body.days]
        if len(set(day_names)) != 7:
            raise HTTPException(
                status_code=422,
                detail="days must contain each day of the week exactly once",
            )
        for d in body.days:
            period_ids = [p.id for p in d.periods]
            if len(set(period_ids)) != len(period_ids):
                raise HTTPException(
                    status_code=422,
                    detail=f"duplicate period id in day {d.day}",
                )
        payload = {"zone_id": zone_id, "days": body.model_dump()["days"]}
        updated = await store.mutate_config(
            apply_schedule_set,
            serial=stored.serial,
            kind="schedule_set",
            target=f"zone:{zone_id}:schedule",
            payload=payload,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        updated_zone = next(
            zc for zc in updated.config.zones if zc.id == zone_id
        )
        return Schedule(zoneId=zone_id, days=list(updated_zone.schedule))

    @app.get("/v1/system", response_model=System, tags=["system"])
    def get_system() -> System:
        """System snapshot: mode, hold, outdoor/humidifier, serial.

        Same projection as /v1/state's `system` field but without zones.
        Useful for clients that only care about whole-house state.
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return _system_response(stored, store.get_telemetry())

    @app.patch("/v1/system", response_model=System, tags=["system"])
    async def patch_system(body: SystemPatch) -> System:
        """Update system-wide settings. Currently only `mode` is writable."""
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        if body.mode is None:
            raise HTTPException(
                status_code=422, detail="no writable fields supplied"
            )
        mode = body.mode.value if hasattr(body.mode, "value") else body.mode
        updated = await store.mutate_config(
            apply_system_mode_set,
            serial=stored.serial,
            kind="system_mode_set",
            target="system",
            payload={"mode": mode},
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return _system_response(updated, store.get_telemetry())

    @app.get(
        "/v1/system/vacation", response_model=VacationConfig, tags=["system"]
    )
    def get_vacation() -> VacationConfig:
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return VacationConfig.model_validate(stored.config.vacation)

    @app.patch(
        "/v1/system/vacation",
        response_model=VacationConfig,
        tags=["system"],
    )
    async def patch_vacation(body: VacationPatch) -> VacationConfig:
        """Update vacation fields — sparse update.

        Supports enabling/disabling via `active`, scheduling via
        `start`/`end`, and vacation-specific setpoints + fan. To exit
        vacation early, send `{"active": false}` — this leaves the
        window in place for "next time" (matching thermostat UX).
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        # `exclude_unset` (not `exclude_none`) so that explicit-null
        # values on nullable fields — `{"end": null}` — count as
        # "supplied" and don't falsely trip the empty-body guard.
        supplied = body.model_dump(exclude_unset=True)
        if not supplied:
            raise HTTPException(
                status_code=422, detail="at least one field must be supplied"
            )
        # datetime → ISO string so the payload is JSON-serializable in
        # pending_writes; apply_vacation_set re-parses as needed.
        for k in ("start", "end"):
            if k in supplied and isinstance(supplied[k], datetime):
                supplied[k] = supplied[k].isoformat()
        updated = await store.mutate_config(
            apply_vacation_set,
            serial=stored.serial,
            kind="vacation_set",
            target="vacation",
            payload=supplied,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return VacationConfig.model_validate(updated.config.vacation)

    @app.get(
        "/v1/system/humidity", response_model=HumidityConfig, tags=["system"]
    )
    def get_humidity() -> HumidityConfig:
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return HumidityConfig.model_validate(stored.config.humidity)

    @app.patch(
        "/v1/system/humidity",
        response_model=HumidityConfig,
        tags=["system"],
    )
    async def patch_humidity(body: HumidityPatch) -> HumidityConfig:
        """Update per-mode humidity targets — sparse update.

        Only the supplied fields are written; unsupplied targets are left
        alone. At least one must be present (empty PATCH → 422). Writing
        to a unit without `<cfghumid>on</cfghumid>` is still accepted —
        the thermostat silently ignores targets when the equipment is
        absent, and rejecting here would pretend we have more knowledge
        than we do.
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        supplied = body.model_dump(exclude_none=True)
        if not supplied:
            raise HTTPException(
                status_code=422, detail="at least one target must be supplied"
            )
        updated = await store.mutate_config(
            apply_humidity_set,
            serial=stored.serial,
            kind="humidity_set",
            target="humidity",
            payload=supplied,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return HumidityConfig.model_validate(updated.config.humidity)

    @app.get(
        "/v1/system/service",
        response_model=ServiceReminders,
        tags=["system"],
    )
    def get_service_reminders() -> ServiceReminders:
        """Combined service-reminder view: commissioning intervals + flags
        from config, life-remaining percentages from the most recent
        telemetry snapshot. Level is None until telemetry has landed."""
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        svc = stored.config.service
        tel = store.get_telemetry()
        snap = tel.snapshot if tel is not None else None
        return ServiceReminders(
            filter=FilterReminder(
                reminderEnabled=svc.filterReminderEnabled,
                intervalMonths=svc.filterIntervalMonths,
                levelPercent=snap.filterLevelPercent if snap else None,
                filterType=svc.filterType,
            ),
            uv=ServiceReminderItem(
                reminderEnabled=svc.uvReminderEnabled,
                intervalMonths=svc.uvIntervalMonths,
                levelPercent=snap.uvLevelPercent if snap else None,
            ),
            humidifier=ServiceReminderItem(
                reminderEnabled=svc.humidifierReminderEnabled,
                intervalMonths=svc.humidifierIntervalMonths,
                levelPercent=snap.humidifierLevelPercent if snap else None,
            ),
            ventilator=ServiceReminderItem(
                reminderEnabled=svc.ventilatorReminderEnabled,
                intervalMonths=svc.ventilatorIntervalMonths,
                levelPercent=snap.ventilatorLevelPercent if snap else None,
            ),
        )

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
        request: Request,
        since: StrictIsoDatetime | None = Query(
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
        _reject_unknown_query(request, {"since", "limit"})
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
        """Spec-shape SSE stream: state.snapshot / state.update / hold.changed.

        Resume protocol: clients pass `Last-Event-ID` on reconnect. If
        the publisher's ring buffer still has events with greater ids,
        we replay them in order; otherwise we re-seed with a fresh
        `state.snapshot`. A first connect (no header) also gets a
        snapshot so the client can paint a full UI before any live
        event arrives. Keepalive every 15s doubles as disconnect probe.
        """
        last_event_id_raw = request.headers.get("last-event-id")
        last_event_id: int | None = None
        if last_event_id_raw is not None:
            try:
                last_event_id = int(last_event_id_raw)
            except ValueError:
                last_event_id = None

        replay: list = []
        need_snapshot = last_event_id is None
        if last_event_id is not None:
            buffered = store.events.replay_since(last_event_id)
            if buffered is None:
                # Caller's id is older than the buffer — re-seed.
                need_snapshot = True
            else:
                replay = buffered

        # Compose the snapshot eagerly (before entering the generator)
        # so _compose_state's 503 for a cold thermostat reaches the
        # client as a proper HTTP error, not a mid-stream disconnect.
        snap_payload: dict | None = None
        if need_snapshot:
            snap_state = _compose_state(
                store.get_config(), store.get_telemetry()
            )
            snap_payload = snap_state.model_dump(mode="json")

        queue = store.events.subscribe()

        async def event_gen():
            try:
                if snap_payload is not None:
                    yield {
                        "id": str(store.events.latest_id),
                        "event": "state.snapshot",
                        "data": _event_json(snap_payload),
                    }
                for ev in replay:
                    yield {
                        "id": str(ev.id),
                        "event": ev.event,
                        "data": _event_json(ev.data),
                    }
                while True:
                    ev = await queue.get()
                    yield {
                        "id": str(ev.id),
                        "event": ev.event,
                        "data": _event_json(ev.data),
                    }
            finally:
                store.events.unsubscribe(queue)

        # ping=15 emits an SSE comment line (`: ping`) every 15s —
        # keeps idle proxies from killing the stream and is ignored by
        # the EventSource API, so it doesn't pollute the spec's event
        # enum. sse_starlette also cancels event_gen() on client
        # disconnect, so we don't poll request.is_disconnected()
        # ourselves.
        return EventSourceResponse(event_gen(), ping=15)

    @app.put(
        "/v1/zones/{zone_id}/hold",
        response_model=Zone,
        tags=["zones"],
    )
    async def set_zone_hold(zone_id: str, body: ZoneHoldRequest) -> Zone:
        """Enable a hold on a zone.

        Writes `<hold>on</hold>`, `<holdActivity>{activity}</holdActivity>`,
        `<otmr>{HH:MM|empty}</otmr>` into the retained config tree, marks
        dirty, enqueues a pending_writes row. The thermostat picks up
        the mutation on its next GET /config, driven by the directive
        channel signalling configHasChanges=true on the next status POST.
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        if not any(zc.id == zone_id for zc in stored.config.zones):
            raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")
        otmr = snap_quarter_hour(body.until) if body.until else ""
        activity = body.activity.value if hasattr(body.activity, "value") else body.activity
        payload = {"zone_id": zone_id, "activity": activity, "otmr": otmr}
        updated = await store.mutate_config(
            apply_zone_hold_set,
            serial=stored.serial,
            kind="zone_hold_set",
            target=f"zone:{zone_id}",
            payload=payload,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return _zone_response(updated, store.get_telemetry(), zone_id)

    @app.delete(
        "/v1/zones/{zone_id}/hold",
        response_model=Zone,
        tags=["zones"],
    )
    async def clear_zone_hold(zone_id: str) -> Zone:
        """Release a zone hold. Idempotent — clearing an already-cleared
        zone is accepted and enqueued; the thermostat's config will just
        be re-written with the same `<hold>off</hold>` state."""
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        if not any(zc.id == zone_id for zc in stored.config.zones):
            raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")
        payload = {"zone_id": zone_id}
        updated = await store.mutate_config(
            apply_zone_hold_clear,
            serial=stored.serial,
            kind="zone_hold_clear",
            target=f"zone:{zone_id}",
            payload=payload,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return _zone_response(updated, store.get_telemetry(), zone_id)

    @app.patch("/v1/zones/{zone_id}", response_model=Zone, tags=["zones"])
    async def patch_zone(zone_id: str, body: ZonePatch) -> Zone:
        """Update a zone's `manual` activity setpoints.

        Writes heat/cool into the zone's `<activity id="manual">` block.
        Unless `activateHold=false`, also flips the zone into manual hold
        so the new setpoints take effect immediately — matching the HA
        climate-card interaction the openapi spec describes.
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        if not any(zc.id == zone_id for zc in stored.config.zones):
            raise HTTPException(status_code=404, detail=f"zone {zone_id} not found")
        if body.heat is None and body.cool is None:
            raise HTTPException(
                status_code=422, detail="provide heat and/or cool"
            )
        payload = {
            "zone_id": zone_id,
            "heat": body.heat,
            "cool": body.cool,
            "activate_hold": body.activateHold,
        }
        updated = await store.mutate_config(
            apply_zone_setpoints_set,
            serial=stored.serial,
            kind="zone_setpoints_set",
            target=f"zone:{zone_id}",
            payload=payload,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return _zone_response(updated, store.get_telemetry(), zone_id)

    @app.put("/v1/system/hold", response_model=System, tags=["system"])
    async def set_system_hold(body: WholeHouseHoldRequest) -> System:
        """Enable the whole-house hold.

        Same shape as zone hold but narrower activity set (home/away/
        sleep/wake — no "manual") and nested under <wholeHouse> instead
        of a zone element. Response is the System view, which uses the
        freshly-updated config for the hold fields.
        """
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        otmr = snap_quarter_hour(body.until) if body.until else ""
        activity = body.activity.value if hasattr(body.activity, "value") else body.activity
        payload = {"activity": activity, "otmr": otmr}
        updated = await store.mutate_config(
            apply_system_hold_set,
            serial=stored.serial,
            kind="system_hold_set",
            target="system",
            payload=payload,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return _system_response(updated, store.get_telemetry())

    @app.delete("/v1/system/hold", response_model=System, tags=["system"])
    async def clear_system_hold() -> System:
        """Release the whole-house hold. Idempotent, like the zone DELETE."""
        stored = store.get_config()
        if stored is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        updated = await store.mutate_config(
            apply_system_hold_clear,
            serial=stored.serial,
            kind="system_hold_clear",
            target="system",
            payload={},
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="no config received yet")
        return _system_response(updated, store.get_telemetry())

    @app.get(
        "/v1/debug/state/{serial}/{kind}",
        include_in_schema=False,
        responses={200: {"content": {"application/xml": {}}}},
    )
    async def debug_state_blob(serial: str, kind: str) -> Response:
        if kind not in ("config", "idu", "odu"):
            raise HTTPException(status_code=404, detail="kind must be config|idu|odu")
        persistence = getattr(store, "_persistence", None)
        if persistence is None:
            raise HTTPException(status_code=503, detail="persistence not attached")
        snap = await persistence.load(serial)
        if snap is None:
            raise HTTPException(status_code=404, detail=f"no snapshot for {serial}")
        blob = getattr(snap, f"{kind}_xml")
        if blob is None:
            raise HTTPException(status_code=404, detail=f"{kind}_xml is null")
        return Response(content=blob, media_type="application/xml")

    # ── Carrier cloud forward-proxy (catch-all, registered LAST) ─────
    # Matches paths shaped /http://host/... or /https://host/... — the
    # encoded absolute-URI form the thermostat uses to reach
    # carrier.com via us. Anything else falls through to FastAPI's
    # default 404. Methods are explicit (no DELETE/HEAD) since the
    # observed usages are GET (firmware checks) + POST/PUT (MyInfinity
    # app round-trips).
    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH"],
        include_in_schema=False,
    )
    async def carrier_passthrough(full_path: str, request: Request) -> Response:
        target = extract_target_url(request)
        if target is None:
            raise HTTPException(status_code=404, detail="not found")
        return await fproxy.forward(request, target)

    return app


def _zone_response(
    stored_config: StoredConfig,
    stored_telemetry: StoredTelemetry | None,
    zone_id: str,
) -> Zone:
    """Build a Zone response for a specific zone after a mutation.

    Delegates to `_build_zone` so mutation responses and `/v1/state`
    stay in lockstep — see that function for the full hold/setpoint
    merge contract.
    """
    zone_config = next(z for z in stored_config.config.zones if z.id == zone_id)
    tz = None
    if stored_telemetry is not None:
        tz = next(
            (z for z in stored_telemetry.snapshot.zones if z.id == zone_id),
            None,
        )
    return _build_zone(zone_config, tz)


def _system_response(
    stored_config: StoredConfig,
    stored_telemetry: StoredTelemetry | None,
) -> System:
    """Build a System response after a whole-house hold mutation.

    Mirrors _zone_response: config is authoritative for hold (it's the
    value we just wrote, and telemetry doesn't carry whole-house hold
    activity), while live fields (outdoor temp, humidifier, etc.) come
    from the most recent telemetry snapshot when present.
    """
    cfg = stored_config.config
    if stored_telemetry is not None:
        snap = stored_telemetry.snapshot
        return System(
            mode=HvacMode(cfg.mode),
            outdoorTemperature=snap.outdoorTemperature,
            humidifierOn=snap.humidifierOn,
            lastReportAt=snap.localTime,
            operatingStatusMessage=snap.operatingStatusMessage,
            serial=stored_config.serial,
            hold=cfg.wholeHouseHold,
        )
    return System(
        mode=HvacMode(cfg.mode),
        serial=stored_config.serial,
        hold=cfg.wholeHouseHold,
    )


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


def _event_json(data) -> str:
    """Serialize an SSE event's `data` payload as JSON.

    Events carry plain dicts or Pydantic-mode-json dumps; a fast path
    through json.dumps (not orjson — the rest of the app doesn't depend
    on it) keeps the wire format predictable for tests.
    """
    import json
    return json.dumps(data, default=str)


app = create_app()
