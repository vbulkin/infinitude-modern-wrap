"""Southbound telemetry handler — replays captured thermostat fixtures."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import (
    parse_notifications,
    parse_system_config,
    parse_telemetry,
)
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_parse_telemetry_boot_sample():
    snap = parse_telemetry(_read("boot_05_status_telemetry.xml"))
    assert snap.outdoorTemperature == 52
    assert snap.operatingStatusMessage == "idle"
    # Fixture has 8 zones in XML but only 2 enabled (id=1, id=2).
    ids = {z.id for z in snap.zones}
    assert ids == {"1", "2"}
    z1 = next(z for z in snap.zones if z.id == "1")
    assert z1.name == "Zone 1"
    assert z1.temperature == 66
    assert z1.humidity == 51
    assert z1.heatSetpoint == 68
    assert z1.coolSetpoint == 74
    # Raw damper=15 → 100%
    assert z1.damperPercent == 100


def test_post_telemetry_returns_directive_and_updates_store():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    body = _read("boot_05_status_telemetry.xml")
    resp = client.post(
        "/systems/0000TEST0000/status",
        content=body,
        headers={"content-type": "application/xml"},
    )
    assert resp.status_code == 200
    # Byte-for-byte match against the captured response shape
    expected = _read("boot_06_status_response.xml")
    assert resp.content == expected

    stored = store.get_telemetry()
    assert stored is not None
    assert stored.serial == "0000TEST0000"
    assert stored.snapshot.outdoorTemperature == 52


def test_post_telemetry_accepts_form_wrapped_body():
    """Real thermostat sends `data=<url-encoded-xml>`; verify we unwrap it."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    import urllib.parse as up
    xml = _read("boot_05_status_telemetry.xml")
    wrapped = b"data=" + up.quote_from_bytes(xml).encode()

    resp = client.post(
        "/systems/0000TEST0000/status",
        content=wrapped,
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert store.get_telemetry() is not None


def test_v1_state_overlays_telemetry():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    # Before any telemetry — canned defaults come through.
    r0 = client.get("/v1/state").json()
    assert r0["system"]["operatingStatusMessage"] == "idle"

    client.post(
        "/systems/0000TEST0000/status",
        content=_read("telemetry_steady.xml"),
        headers={"content-type": "application/xml"},
    )

    r1 = client.get("/v1/state").json()
    # telemetry_steady has mode=hpheat (runtime state), oat=52, two zones live.
    assert r1["system"]["outdoorTemperature"] == 52
    assert r1["system"]["serial"] == "0000TEST0000"
    zone1 = next(z for z in r1["zones"] if z["id"] == "1")
    assert zone1["temperature"] == 66
    assert zone1["damperPercent"] == 100


def test_v1_healthz_reflects_telemetry_receipt():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    r0 = client.get("/v1/healthz").json()
    assert r0["components"]["thermostat"]["status"] == "unreachable"
    assert r0["status"] == "degraded"

    client.post(
        "/systems/0000TEST0000/status",
        content=_read("telemetry_steady.xml"),
        headers={"content-type": "application/xml"},
    )

    r1 = client.get("/v1/healthz").json()
    assert r1["components"]["thermostat"]["status"] == "healthy"
    assert r1["status"] == "healthy"
    assert r1["components"]["thermostat"]["lastContactAgeSeconds"] is not None


def test_alive_heartbeat():
    client = TestClient(create_app())
    r = client.get("/Alive")
    assert r.status_code == 200
    assert r.content == b"alive"


def test_parse_system_config_boot_dump():
    cfg = parse_system_config(_read("boot_01_system_config.xml"))
    assert cfg.mode == "cool"
    assert cfg.wholeHouseHold.active is False
    # 8 zones in XML; 2 enabled (id=1, id=2) — matches the live household.
    ids = {z.id for z in cfg.zones}
    assert ids == {"1", "2"}


def test_parse_system_config_opmode_change():
    """Wall-panel mode switch flips config.mode from cool → auto."""
    cfg = parse_system_config(_read("change_opmode_system.xml"))
    assert cfg.mode == "auto"


def test_parse_system_config_activities_and_schedule():
    cfg = parse_system_config(_read("boot_01_system_config.xml"))
    z1 = next(z for z in cfg.zones if z.id == "1")
    # Five closed-enum activities in fixed order.
    assert [a.id for a in z1.activities] == ["home", "away", "sleep", "wake", "manual"]
    home = next(a for a in z1.activities if a.id == "home")
    assert home.heat == 68 and home.cool == 74 and home.fan == "low"
    # Seven-day schedule; period 1 on Sunday is wake @ 08:00.
    assert [d.day for d in z1.schedule] == [
        "Sunday", "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday",
    ]
    sunday = next(d for d in z1.schedule if d.day == "Sunday")
    p1 = next(p for p in sunday.periods if p.id == 1)
    assert p1.activity == "wake" and p1.time == "08:00" and p1.enabled is True


def test_v1_zone_activities_and_schedule_endpoints():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    # Before any config, both endpoints 404.
    assert client.get("/v1/zones/1/activities").status_code == 404
    assert client.get("/v1/zones/1/schedule").status_code == 404

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    acts = client.get("/v1/zones/1/activities").json()
    assert [a["id"] for a in acts] == ["home", "away", "sleep", "wake", "manual"]

    sched = client.get("/v1/zones/1/schedule").json()
    assert sched["zoneId"] == "1"
    assert len(sched["days"]) == 7
    sunday = next(d for d in sched["days"] if d["day"] == "Sunday")
    assert sunday["periods"][0] == {
        "id": 1, "activity": "wake", "time": "08:00", "enabled": True,
    }

    # Unknown zone id → 404.
    assert client.get("/v1/zones/9/activities").status_code == 404
    assert client.get("/v1/zones/9/schedule").status_code == 404


def test_post_system_config_updates_store():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    resp = client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    assert resp.status_code == 200
    stored = store.get_config()
    assert stored is not None
    assert stored.config.mode == "cool"


def test_v1_state_after_config_then_telemetry():
    """Realistic boot order: full config POST, then telemetry POST.
    /v1/state should surface both — config's mode plus telemetry's live values.
    """
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("change_opmode_system.xml"),
        headers={"content-type": "application/xml"},
    )
    client.post(
        "/systems/0000TEST0000/status",
        content=_read("telemetry_steady.xml"),
        headers={"content-type": "application/xml"},
    )
    state = client.get("/v1/state").json()
    assert state["system"]["mode"] == "auto"          # from config
    assert state["system"]["outdoorTemperature"] == 52  # from telemetry
    assert state["system"]["serial"] == "0000TEST0000"


def test_metadata_posts_accepted_without_parse():
    """The thermostat's profile/dealer/idu_config/odu_config metadata
    POSTs must 200 OK so it doesn't retry."""
    client = TestClient(create_app())
    for path in ("profile", "dealer", "idu_config", "odu_config"):
        r = client.post(
            f"/systems/0000TEST0000/{path}",
            content=_read("boot_02_profile.xml"),
            headers={"content-type": "application/xml"},
        )
        assert r.status_code == 200, f"{path} should 200"


def test_parse_notifications_extracts_three_change_ids():
    cases = [
        ("change_opmode_notifications.xml",   "OP_MODE",        None),
        ("change_schedule_notifications.xml", "ZONE_SCHEDULE",  "1"),
        ("change_setpoint_notifications.xml", "ZONE_SETPOINTS", "1"),
    ]
    for fixture, change_id, zone in cases:
        events = parse_notifications(_read(fixture))
        assert len(events) == 1
        ev = events[0]
        assert ev.type == "confirmation"
        assert ev.code == 200
        assert len(ev.changes) == 1
        assert ev.changes[0].id == change_id
        assert ev.changes[0].zone == zone


def test_directive_flips_dirty_flag_and_config_post_clears_it():
    """Dirty-flag lifecycle end-to-end:
      1. clean store   → configHasChanges=false
      2. mark_dirty    → configHasChanges=true
      3. full-config POST clears it → next telemetry back to false
    """
    import asyncio
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    def _telemetry_response() -> bytes:
        return client.post(
            "/systems/0000TEST0000/status",
            content=_read("telemetry_steady.xml"),
            headers={"content-type": "application/xml"},
        ).content

    assert b"<configHasChanges>false</configHasChanges>" in _telemetry_response()

    asyncio.run(store.mark_config_dirty())
    assert b"<configHasChanges>true</configHasChanges>" in _telemetry_response()

    # Thermostat responds to the directive by re-uploading full config.
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    assert b"<configHasChanges>false</configHasChanges>" in _telemetry_response()


async def test_store_broadcasts_notifications_to_subscribers():
    store = StateStore()
    q1 = store.subscribe()
    q2 = store.subscribe()
    events = parse_notifications(_read("change_opmode_notifications.xml"))
    await store.append_notifications("0000TEST0000", events)

    sn1 = q1.get_nowait()
    sn2 = q2.get_nowait()
    assert sn1.event.changes[0].id == "OP_MODE"
    assert sn2.serial == "0000TEST0000"
    assert q1.empty() and q2.empty()

    store.unsubscribe(q1)
    store.unsubscribe(q2)
    assert store.subscriber_count == 0


def test_sse_events_route_registered():
    """/v1/events is mounted as a GET route.

    End-to-end HTTP-level SSE testing needs a real uvicorn server —
    both TestClient and httpx.ASGITransport buffer the full response
    before returning, so they can't exercise an endpoint that never
    closes. The store fan-out test above covers the broadcast logic;
    this smoke-tests that the route is wired.
    """
    app = create_app()
    events_route = next(
        (r for r in app.routes if getattr(r, "path", None) == "/v1/events"),
        None,
    )
    assert events_route is not None
    assert "GET" in getattr(events_route, "methods", set())


def test_post_notifications_appends_to_store():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    for fixture in (
        "change_opmode_notifications.xml",
        "change_schedule_notifications.xml",
        "change_setpoint_notifications.xml",
    ):
        r = client.post(
            "/systems/0000TEST0000/notifications",
            content=_read(fixture),
            headers={"content-type": "application/xml"},
        )
        assert r.status_code == 200

    stored = store.recent_notifications()
    assert [sn.event.changes[0].id for sn in stored] == [
        "OP_MODE", "ZONE_SCHEDULE", "ZONE_SETPOINTS",
    ]
    assert all(sn.serial == "0000TEST0000" for sn in stored)
