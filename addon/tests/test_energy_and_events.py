"""Energy snapshot + equipment-events parsers + endpoints.

The thermostat POSTs `/systems/{serial}/energy` (~daily) with per-mode
runtime hours and SEER/HSPF efficiency ratings — the data source the
MyInfinity app's energy dashboard reads from. `/systems/{serial}/equipment_events`
carries fault history on demand. Pre-alpha.33 both fell through the
metadata-fallback handler — accepted-and-discarded with a one-line log.
This release parses + stores + exposes them at /v1/system/{energy,events}.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import parse_energy, parse_equipment_events
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ── Pure parsers ──────────────────────────────────────────────────────


def test_parse_energy_extracts_efficiency_ratings():
    e = parse_energy(_read("energy.xml"))
    assert e.seer == 15.0
    assert e.hspf == 8.8


def test_parse_energy_per_mode_flags():
    e = parse_energy(_read("energy.xml"))
    # Live install: cooling/hpheat/eheat/reheat/fan are display=on,
    # gas/fangas/looppump are display=off. All except looppump
    # are enabled=on.
    assert e.modes["cooling"].display is True
    assert e.modes["cooling"].enabled is True
    assert e.modes["hpheat"].display is True
    assert e.modes["gas"].display is False
    assert e.modes["gas"].enabled is True
    assert e.modes["looppump"].display is False
    assert e.modes["looppump"].enabled is False


def test_parse_energy_period_counters():
    """Live fixture has 6 periods (day1/day2/month1/month2/year1/year2)
    with hour counts per mode. Spot-check a few — heat-pump install
    so hpheat dominates day1, cooling dominates the year totals."""
    e = parse_energy(_read("energy.xml"))
    assert len(e.usage) == 6
    by_id = {p.id: p for p in e.usage}
    assert by_id["day1"].hpheat == 17
    assert by_id["day1"].cooling == 0
    assert by_id["day2"].hpheat == 6
    assert by_id["year1"].cooling == 3328
    assert by_id["year1"].hpheat == 37
    assert by_id["year1"].eheat == 29
    assert by_id["year2"].cooling == 2887


def test_parse_equipment_events_extracts_fault_list():
    """Live fixture carries one historical event: a Zone-1 communication
    error from April 9th, no longer active."""
    ee = parse_equipment_events(_read("equipment_events.xml"))
    assert len(ee.events) == 1
    ev = ee.events[0]
    assert ev.code == "16"
    assert ev.source == "ZN1"
    assert "COMMUNICATION ERROR" in ev.description
    assert ev.localTime == "2026-04-09T00:13:00"
    assert ev.occurrences == 1
    assert ev.active is False


def test_parse_equipment_events_empty_list():
    """Fresh install with no faults: `<equipment_events><events/></equipment_events>`."""
    ee = parse_equipment_events(
        b'<?xml version="1.0"?><equipment_events version="1.7"><events/></equipment_events>'
    )
    assert ee.events == []


# ── Southbound POST handlers ──────────────────────────────────────────


def test_post_energy_stores_and_serves_via_v1_endpoint():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    # Endpoint 404s before first POST.
    r = client.get("/v1/system/energy")
    assert r.status_code == 404

    r = client.post(
        "/systems/2013W000855/energy",
        content=_read("energy.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200

    r = client.get("/v1/system/energy")
    assert r.status_code == 200
    body = r.json()
    assert body["seer"] == 15.0
    assert body["hspf"] == 8.8
    # Periods returned as a list with id+counters.
    by_id = {p["id"]: p for p in body["usage"]}
    assert by_id["day1"]["hpheat"] == 17
    assert by_id["year1"]["cooling"] == 3328


def test_post_equipment_events_stores_and_serves_via_v1_endpoint():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    r = client.get("/v1/system/events")
    assert r.status_code == 404

    r = client.post(
        "/systems/2013W000855/equipment_events",
        content=_read("equipment_events.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200

    r = client.get("/v1/system/events")
    assert r.status_code == 200
    body = r.json()
    assert len(body["events"]) == 1
    ev = body["events"][0]
    assert ev["code"] == "16"
    assert ev["source"] == "ZN1"


# ── Zone.conditioningStage (multi-stage HP/AC visibility) ────────────


def test_zone_conditioning_stage_from_staged1():
    """Telemetry's `<zoneconditioning>staged1_heat</zoneconditioning>`
    surfaces as Zone.conditioningStage=1 + conditioning=HEATING."""
    raw = _read("heatpump_status_telemetry.xml").replace(
        b"<zoneconditioning>active_heat</zoneconditioning>",
        b"<zoneconditioning>staged1_heat</zoneconditioning>",
        1,
    )
    from infinitude_proxy.parser import parse_telemetry
    snap = parse_telemetry(raw)
    z1 = next(z for z in snap.zones if z.id == "1")
    assert z1.conditioning == "heating"
    assert z1.conditioningStage == 1


def test_zone_conditioning_stage_from_staged2():
    raw = _read("heatpump_status_telemetry.xml").replace(
        b"<zoneconditioning>active_heat</zoneconditioning>",
        b"<zoneconditioning>staged2_cool</zoneconditioning>",
        1,
    )
    from infinitude_proxy.parser import parse_telemetry
    snap = parse_telemetry(raw)
    z1 = next(z for z in snap.zones if z.id == "1")
    assert z1.conditioning == "cooling"
    assert z1.conditioningStage == 2


def test_zone_conditioning_stage_none_for_active_heat():
    """`active_heat` is single-stage full output — no stage to surface."""
    from infinitude_proxy.parser import parse_telemetry
    snap = parse_telemetry(_read("heatpump_status_telemetry.xml"))
    z1 = next(z for z in snap.zones if z.id == "1")
    assert z1.conditioning == "heating"
    assert z1.conditioningStage is None


def test_v1_state_zone_carries_conditioningStage():
    """End-to-end: stage info from telemetry surfaces on the API."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/2013W000855",
        content=_read("heatpump_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    raw = _read("heatpump_status_telemetry.xml").replace(
        b"<zoneconditioning>active_heat</zoneconditioning>",
        b"<zoneconditioning>staged2_heat</zoneconditioning>",
        1,
    )
    client.post(
        "/systems/2013W000855/status",
        content=raw,
        headers={"content-type": "application/xml"},
    )

    state = client.get("/v1/state").json()
    z1 = next(z for z in state["zones"] if z["id"] == "1")
    assert z1["conditioning"] == "heating"
    assert z1["conditioningStage"] == 2
