"""Slice 8 — GET /v1/system/service.

Read-only view combining config-side reminder commissioning (intervals,
flags, filter type) with telemetry-side life-remaining levels. Surfaces
the four reminder-tracked services: filter, UV, humidifier, ventilator.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import (
    parse_system_config_with_tree,
    parse_telemetry,
)
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ── Parser ────────────────────────────────────────────────────────────

def test_parse_service_reads_intervals_and_flags():
    _, config = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    svc = config.service
    assert svc.filterIntervalMonths == 3
    assert svc.uvIntervalMonths == 12
    assert svc.humidifierIntervalMonths == 12
    assert svc.ventilatorIntervalMonths == 90
    assert svc.filterReminderEnabled is True
    assert svc.uvReminderEnabled is True
    assert svc.humidifierReminderEnabled is True
    assert svc.ventilatorReminderEnabled is True
    assert svc.filterType == "air filter"


def test_parse_telemetry_surfaces_service_levels():
    snap = parse_telemetry(_read("boot_05_status_telemetry.xml"))
    assert snap.filterLevelPercent == 10
    assert snap.uvLevelPercent == 0
    assert snap.humidifierLevelPercent == 0
    assert snap.ventilatorLevelPercent == 0


def test_parse_telemetry_levels_none_when_fields_missing():
    """Older or stripped fixtures may omit the level tags; parser must
    return None rather than 0 so consumers can distinguish 'unknown' from
    'service due now'."""
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<status>
  <localTime>2026-04-20T10:00:00-04:00</localTime>
  <oat>52</oat>
  <oprstsmsg>idle</oprstsmsg>
  <humid>off</humid>
  <zones/>
</status>"""
    snap = parse_telemetry(xml)
    assert snap.filterLevelPercent is None
    assert snap.uvLevelPercent is None
    assert snap.humidifierLevelPercent is None
    assert snap.ventilatorLevelPercent is None


# ── HTTP ──────────────────────────────────────────────────────────────

def test_get_service_returns_combined_view():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    client.post(
        "/systems/0000TEST0000/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.get("/v1/system/service")
    assert resp.status_code == 200
    body = resp.json()
    assert body["filter"]["intervalMonths"] == 3
    assert body["filter"]["reminderEnabled"] is True
    assert body["filter"]["levelPercent"] == 10
    assert body["filter"]["filterType"] == "air filter"
    assert body["uv"]["intervalMonths"] == 12
    assert body["uv"]["levelPercent"] == 0
    assert body["humidifier"]["intervalMonths"] == 12
    assert body["ventilator"]["intervalMonths"] == 90


def test_get_service_levels_none_before_telemetry():
    """Config has landed but no telemetry yet — levelPercent must be
    null rather than a fabricated 0 or 100. Reminders still reflect
    the config-side flags + intervals."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.get("/v1/system/service")
    assert resp.status_code == 200
    body = resp.json()
    assert body["filter"]["levelPercent"] is None
    assert body["uv"]["levelPercent"] is None
    assert body["humidifier"]["levelPercent"] is None
    assert body["ventilator"]["levelPercent"] is None
    # Config-side fields still populated.
    assert body["filter"]["intervalMonths"] == 3
    assert body["filter"]["reminderEnabled"] is True


def test_get_service_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    resp = client.get("/v1/system/service")
    assert resp.status_code == 404
    # Spec-compliant error envelope from register_error_handlers.
    assert resp.json()["error"]["code"] == "not_found"


def test_get_service_openapi_schema_exposes_endpoint():
    """Contract guard: the endpoint must appear in the generated schema
    so clients generated from openapi.yaml discover it."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    assert "/v1/system/service" in schema["paths"]
    assert "get" in schema["paths"]["/v1/system/service"]
