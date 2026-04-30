"""Southbound telemetry handler — replays captured thermostat fixtures."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import (
    parse_idu_config,
    parse_notifications,
    parse_odu_config,
    parse_system_config,
    parse_system_config_with_tree,
    parse_telemetry,
    serialize_config_tree,
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


def test_parse_telemetry_accepts_heat_pump_modes():
    """Heat-pump installs report telemetry <mode> as 'hpheat' / 'hpcool'.

    Until alpha.17 these crashed parse_telemetry on the HvacMode enum
    coercion, returning 500 to every status post and stranding the
    thermostat as 'unreachable' from HA's perspective. The enum now
    carries the heat-pump variants explicitly.
    """
    raw = _read("boot_05_status_telemetry.xml").replace(
        b"<mode>off</mode>", b"<mode>hpheat</mode>", 1
    )
    snap = parse_telemetry(raw)
    assert snap.systemMode == "hpheat"


def test_parse_telemetry_unknown_mode_falls_back_to_off():
    """An unfamiliar <mode> value must not break the entire status path —
    parser falls through to OFF so the rest of the snapshot lands. The
    crash on unknown enum values was the bug behind alpha.16's "thermostat
    unreachable" symptom on heat-pump installs.
    """
    raw = _read("boot_05_status_telemetry.xml").replace(
        b"<mode>off</mode>", b"<mode>future_mode_x</mode>", 1
    )
    snap = parse_telemetry(raw)
    assert snap.systemMode == "off"


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

    # Cold start — no config, no telemetry. Endpoint is 503.
    r0 = client.get("/v1/state")
    assert r0.status_code == 503

    # Seed config, then telemetry (natural boot order).
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
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


def test_release_notes_stub_returns_empty_200():
    """Thermostat polls /releaseNotes/{model}-{firmware}.txt; a 404 triggers
    a tight retry loop, so we answer empty 200 like upstream Perl."""
    client = TestClient(create_app())
    r = client.get("/releaseNotes/systxbbec-14.02.txt")
    assert r.status_code == 200
    assert r.content == b""
    # Nested paths too — the firmware occasionally uses subdirectories
    # and the path parameter must pass them through intact.
    r2 = client.get("/releaseNotes/sub/path/file.txt")
    assert r2.status_code == 200


def test_parse_system_config_boot_dump():
    cfg = parse_system_config(_read("boot_01_system_config.xml"))
    assert cfg.mode == "cool"
    assert cfg.wholeHouseHold.active is False
    # 8 zones in XML; 2 enabled (id=1, id=2) — matches the live household.
    ids = {z.id for z in cfg.zones}
    assert ids == {"1", "2"}


def test_config_parse_serialize_is_byte_identical():
    """Regression anchor: parse → serialize must not alter the inner
    <config> bytes for any captured thermostat payload.

    The thermostat's XML parser is strict — a self-closing `<otmr/>`
    round-tripped to `<otmr></otmr>` (or vice versa) causes it to
    silently reject the next /config pull and stick with its prior
    state. Mutations are always applied on a parsed tree and the tree
    is serialized back to the thermostat, so any asymmetry in the
    parser/serializer pair is a latent write-path bug across every
    REPLAY_REGISTRY handler. This test holds the invariant tight.

    The boot capture wraps as `<system version="1.7"><config>…</config></system>`;
    we compare the inner `<config>` subtree (which is what GET /systems/{serial}/config
    actually emits over the wire).
    """
    import re
    orig = _read("boot_01_system_config.xml")
    tree, _ = parse_system_config_with_tree(orig)
    ser = serialize_config_tree(tree)
    m = re.search(rb"<config>.*</config>", orig, re.S)
    assert m is not None, "fixture must contain a <config> subtree"
    orig_inner = m.group(0)
    ser_inner = ser.split(b"?>\n", 1)[1]
    assert ser_inner == orig_inner, (
        "parse→serialize is not byte-identical — "
        "a shape divergence will cause the thermostat to silently reject "
        "the next config pull. Look for lxml serialization flags or a "
        "parser step that rewrites element text."
    )


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


def test_parse_system_config_vacation_and_humidity():
    cfg = parse_system_config(_read("boot_01_system_config.xml"))
    # Fixture has vacat=off with 60/80 setpoints retained from the last
    # vacation; no active window so start/end are None.
    assert cfg.vacation.active is False
    assert cfg.vacation.start is None and cfg.vacation.end is None
    assert cfg.vacation.heatSetpoint == 60
    assert cfg.vacation.coolSetpoint == 80
    assert cfg.vacation.fan == "off"
    # Humidifier hardware installed (cfghumid=on), fan runs with it,
    # but the live household hasn't set any per-mode targets.
    assert cfg.humidity.equipmentInstalled is True
    assert cfg.humidity.humidifierFan is True
    assert cfg.humidity.targetHome is None
    assert cfg.humidity.targetAway is None
    assert cfg.humidity.targetVacation is None


def test_v1_system_vacation_and_humidity_endpoints():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    assert client.get("/v1/system/vacation").status_code == 404
    assert client.get("/v1/system/humidity").status_code == 404

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    vac = client.get("/v1/system/vacation").json()
    assert vac["active"] is False
    assert vac["heatSetpoint"] == 60 and vac["coolSetpoint"] == 80

    hum = client.get("/v1/system/humidity").json()
    assert hum["equipmentInstalled"] is True
    assert hum["targetHome"] is None


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
    """The thermostat's profile/dealer metadata POSTs must 200 OK so it
    doesn't retry. idu_config/odu_config are now parsed — covered by
    their own tests."""
    client = TestClient(create_app())
    for path in ("profile", "dealer"):
        r = client.post(
            f"/systems/0000TEST0000/{path}",
            content=_read("boot_02_profile.xml"),
            headers={"content-type": "application/xml"},
        )
        assert r.status_code == 200, f"{path} should 200"


def test_parse_idu_config_boot_sample():
    idu = parse_idu_config(_read("boot_03_idu_config.xml"))
    assert idu.type == "fancoilelectric"
    assert idu.elevationFeet == 800
    # <gtermavail>on</gtermavail> in the fixture
    assert idu.auxiliaryTerminalAvailable is True


def test_parse_odu_config_boot_sample():
    odu = parse_odu_config(_read("boot_04_odu_config.xml"))
    assert odu.type == "hp2stgnoncomm"
    assert odu.coolAirflowProfile == "comfort"
    assert odu.heatAirflowProfile == "comfort"
    assert odu.dehumidifyAirflowProfile == "normal"
    # Both lockouts are "none" in the fixture — round-trips as None.
    assert odu.coolLockoutTemp is None
    assert odu.heatLockoutTemp is None
    assert odu.defrostInterval == "auto"


def test_post_idu_and_odu_config_updates_store():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    r = client.post(
        "/systems/0000TEST0000/idu_config",
        content=_read("boot_03_idu_config.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    stored_idu = store.get_idu()
    assert stored_idu is not None
    assert stored_idu.serial == "0000TEST0000"
    assert stored_idu.config.type == "fancoilelectric"

    r = client.post(
        "/systems/0000TEST0000/odu_config",
        content=_read("boot_04_odu_config.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    stored_odu = store.get_odu()
    assert stored_odu is not None
    assert stored_odu.config.type == "hp2stgnoncomm"


def test_v1_system_idu_and_odu_endpoints():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    assert client.get("/v1/system/idu").status_code == 404
    assert client.get("/v1/system/odu").status_code == 404

    client.post(
        "/systems/0000TEST0000/idu_config",
        content=_read("boot_03_idu_config.xml"),
        headers={"content-type": "application/xml"},
    )
    client.post(
        "/systems/0000TEST0000/odu_config",
        content=_read("boot_04_odu_config.xml"),
        headers={"content-type": "application/xml"},
    )

    idu = client.get("/v1/system/idu").json()
    assert idu["type"] == "fancoilelectric"
    assert idu["elevationFeet"] == 800
    assert idu["auxiliaryTerminalAvailable"] is True

    odu = client.get("/v1/system/odu").json()
    assert odu["type"] == "hp2stgnoncomm"
    assert odu["coolAirflowProfile"] == "comfort"
    assert odu["coolLockoutTemp"] is None
    assert odu["defrostInterval"] == "auto"


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


def test_directive_dirty_flag_optimistic_clear_in_status_handler():
    """Dirty-flag lifecycle matches upstream Perl's optimistic pattern:
      1. clean store             → configHasChanges=false, pingRate=12
      2. mark_dirty              → the NEXT status POST returns
                                   configHasChanges=true, pingRate=20
                                   AND clears the flag in the same step
      3. the status POST AFTER   → configHasChanges=false, pingRate=12
                                   (no additional config POST needed;
                                   clear is optimistic, not earned by the
                                   thermostat actually fetching /config)
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

    r = _telemetry_response()
    assert b"<configHasChanges>false</configHasChanges>" in r
    assert b"<pingRate>12</pingRate>" in r

    asyncio.run(store.mark_config_dirty())
    r = _telemetry_response()
    assert b"<configHasChanges>true</configHasChanges>" in r
    assert b"<pingRate>20</pingRate>" in r

    # Optimistic clear: the dirty signal was consumed by the status
    # handler above; the next status POST already sees clean state.
    # The thermostat follows up with a GET /config (tested separately)
    # but that GET is NOT what clears the flag.
    r = _telemetry_response()
    assert b"<configHasChanges>false</configHasChanges>" in r
    assert b"<pingRate>12</pingRate>" in r


def test_post_system_config_does_not_clear_dirty_flag():
    """Config POST from the thermostat is a data refresh, not a write
    acknowledgement. The dirty flag is managed solely by the status
    handler (set via mark_config_dirty, cleared via take_config_dirty)."""
    import asyncio
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    asyncio.run(store.mark_config_dirty())
    # A config POST arriving while dirty MUST NOT clear the flag —
    # the thermostat might be doing an unrelated boot-time upload and
    # the pending northbound edit still needs to be signalled.
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    assert store.config_dirty is True


def test_get_systems_config_404_before_boot_post():
    """Thermostat-facing GET /config returns 404 until the boot-time
    POST to /systems/{serial} populates the store. Serving empty or
    stale bytes would send the thermostat into a re-sync loop."""
    client = TestClient(create_app())
    r = client.get("/systems/0000TEST0000/config")
    assert r.status_code == 404


def test_get_systems_config_serves_stored_tree():
    """After the thermostat's boot POST, GET /config serves the
    retained <config> subtree as `<?xml ...?>\\n<config>...</config>`
    — outer <system> stripped, matching the live Mojolicious shape."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    r = client.get("/systems/0000TEST0000/config")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    body = r.content
    assert body.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\n<config>')
    assert body.rstrip().endswith(b"</config>")
    # No <system> wrapper on the wire (the POST had one; GET strips
    # it). Match the tag with its version attribute to avoid false hits
    # from <systemCFM>, <staticPressure>'s neighbors, etc.
    assert b"<system " not in body and b"<system>" not in body
    # Round-trip spot checks against the known fixture state.
    assert b"<mode>cool</mode>" in body


async def test_store_appends_notifications_to_ring_buffer():
    """Thermostat notifications land in the ring buffer only.

    The SSE stream no longer carries raw thermostat notifications
    (openapi EventEnvelope enum is state/hold/health). Subscribers
    live on `store.events`, not on the legacy per-notification fan-out.
    """
    store = StateStore()
    events = parse_notifications(_read("change_opmode_notifications.xml"))
    await store.append_notifications("0000TEST0000", events)

    buffered = store.recent_notifications()
    assert len(buffered) >= 1
    assert buffered[-1].event.changes[0].id == "OP_MODE"
    assert buffered[-1].serial == "0000TEST0000"
    # No SSE subscribers created; spec-event publisher has none.
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


def test_v1_notifications_empty_buffer_returns_empty_list():
    client = TestClient(create_app())
    r = client.get("/v1/notifications")
    assert r.status_code == 200
    assert r.json() == []


def test_v1_notifications_returns_recent_entries_oldest_first():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    for fixture in (
        "change_opmode_notifications.xml",
        "change_schedule_notifications.xml",
        "change_setpoint_notifications.xml",
    ):
        client.post(
            "/systems/0000TEST0000/notifications",
            content=_read(fixture),
            headers={"content-type": "application/xml"},
        )

    body = client.get("/v1/notifications").json()
    # Oldest-first; deque preserves insertion order.
    assert [n["event"]["changes"][0]["id"] for n in body] == [
        "OP_MODE", "ZONE_SCHEDULE", "ZONE_SETPOINTS",
    ]
    # Envelope shape matches the SSE frame contract.
    n0 = body[0]
    assert n0["serial"] == "0000TEST0000"
    assert "receivedAt" in n0
    assert n0["event"]["type"] == "confirmation"


def test_v1_notifications_since_filter_excludes_older_and_equal():
    """`since` is strictly greater-than — a client passing the cursor
    of its last-seen event must not get that event back."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000/notifications",
        content=_read("change_opmode_notifications.xml"),
        headers={"content-type": "application/xml"},
    )
    first = client.get("/v1/notifications").json()
    cursor = first[0]["receivedAt"]

    client.post(
        "/systems/0000TEST0000/notifications",
        content=_read("change_setpoint_notifications.xml"),
        headers={"content-type": "application/xml"},
    )
    body = client.get(f"/v1/notifications?since={cursor}").json()
    assert len(body) == 1
    assert body[0]["event"]["changes"][0]["id"] == "ZONE_SETPOINTS"


def test_v1_notifications_limit_caps_results():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    for _ in range(3):
        client.post(
            "/systems/0000TEST0000/notifications",
            content=_read("change_opmode_notifications.xml"),
            headers={"content-type": "application/xml"},
        )

    body = client.get("/v1/notifications?limit=2").json()
    assert len(body) == 2

    # Out-of-range limit is rejected by FastAPI validation.
    assert client.get("/v1/notifications?limit=0").status_code == 422
    assert client.get("/v1/notifications?limit=51").status_code == 422


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
