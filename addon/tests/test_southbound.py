"""Southbound telemetry handler — replays captured thermostat fixtures."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import parse_telemetry
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
