"""ODU + IDU live-runtime status parsers + endpoints (alpha.34).

Pre-alpha.34 the thermostat's `/odu_status` and `/idu_status` POSTs
fell through the metadata-fallback handler. They carry the live-data
the MyInfinity app shows on its diagnostic screen — compressor
stage + RPM, refrigerant pressures, blower RPM, static pressure,
expansion-valve position, lockout state. This release parses,
stores, and exposes both at /v1/system/{odu_status,idu_status}.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import (
    _parse_stage,
    parse_idu_status,
    parse_odu_status,
)
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ── opstat → integer stage extraction ────────────────────────────────


def test_parse_stage_recognizes_stage_n_strings():
    assert _parse_stage("Stage 0") == 0
    assert _parse_stage("Stage 1") == 1
    assert _parse_stage("Stage 2") == 2
    # Whitespace tolerated.
    assert _parse_stage("  Stage 1  ") == 1


def test_parse_stage_returns_none_for_off_and_unknown():
    assert _parse_stage("off") is None
    assert _parse_stage("idle") is None
    assert _parse_stage("") is None
    assert _parse_stage("Stage X") is None
    assert _parse_stage("StageOne") is None


# ── ODU status (idle fixture: HP at Stage 0, all sensors `na`) ───────


def test_parse_odu_status_idle_fixture_extracts_stage_and_metadata():
    """Live fixture from a heat-pump install, captured while idle.
    `<opstat>Stage 0</opstat>` + `<opmode>off</opmode>` + most sensor
    fields literal `na` / `invalid`. The parser should surface the
    stage info and coerce the placeholders to None."""
    s = parse_odu_status(_read("odu_status_idle.xml"))
    assert s.odutype == "hp2stgnoncomm"
    assert s.opstat == "Stage 0"
    assert s.operatingStage == 0
    assert s.opmode == "off"
    # OAT is one of the few fields with a real reading even when idle.
    assert s.outdoorTemperature == 72
    assert s.blowerRpm == 716
    assert s.iduCfm == 912
    # All `na`/`invalid` sensors → None.
    assert s.coilTemperature is None         # <oducoiltmp>na</...>
    assert s.leavingAirTemperature is None   # <lat>invalid</...>
    assert s.compressorRpm is None           # <comprpm>na</...>
    assert s.suctionPressure is None
    assert s.suctionTemperature is None
    assert s.suctionSuperheat is None
    assert s.dischargeTemperature is None
    assert s.lineVoltage is None
    # Real values for the always-reading fields.
    assert s.expansionValvePosition == 0
    assert s.lockoutTime == 0
    assert s.staticPressure == 0.37
    assert s.enteringRefrigerantTemperature == 0.0
    # Lockout / curtail off.
    assert s.lockoutActive is False
    assert s.curtailActive is False
    # Empty stage-availability elements coerce to None.
    assert s.availMinHeatStage is None
    assert s.availMaxHeatStage is None
    assert s.opMaxCoolStage is None


def test_parse_odu_status_running_fixture_populates_compressor_data():
    """Synthesised running state — replace `na` with real values to
    cover the populated-sensor path."""
    raw = _read("odu_status_idle.xml")
    raw = raw.replace(b"<opstat>Stage 0</opstat>", b"<opstat>Stage 2</opstat>")
    raw = raw.replace(b"<opmode>off</opmode>", b"<opmode>hpheat</opmode>")
    raw = raw.replace(b"<comprpm>na</comprpm>", b"<comprpm>3450</comprpm>")
    raw = raw.replace(b"<suctpress>na</suctpress>", b"<suctpress>87.5</suctpress>")
    raw = raw.replace(b"<sucttemp>na</sucttemp>", b"<sucttemp>52</sucttemp>")
    raw = raw.replace(b"<suctsupheat>na</suctsupheat>", b"<suctsupheat>10.5</suctsupheat>")
    raw = raw.replace(b"<dischargetmp>na</dischargetmp>", b"<dischargetmp>180</dischargetmp>")
    raw = raw.replace(b"<oducoiltmp>na</oducoiltmp>", b"<oducoiltmp>45</oducoiltmp>")
    raw = raw.replace(b"<lat>invalid</lat>", b"<lat>105</lat>")

    s = parse_odu_status(raw)
    assert s.operatingStage == 2
    assert s.opmode == "hpheat"
    assert s.compressorRpm == 3450
    assert s.suctionPressure == 87.5
    assert s.suctionTemperature == 52
    assert s.suctionSuperheat == 10.5
    assert s.dischargeTemperature == 180
    assert s.coilTemperature == 45
    assert s.leavingAirTemperature == 105


# ── IDU status (idle fixture: fancoil off) ───────────────────────────


def test_parse_idu_status_idle_fixture():
    s = parse_idu_status(_read("idu_status_idle.xml"))
    assert s.idutype == "fancoilelectric"
    assert s.opstat == "off"
    assert s.operatingStage is None  # "off" doesn't parse to a stage int
    assert s.iduCfm == 912
    assert s.blowerRpm == 721
    assert s.staticPressure == 0.37
    # `invalid` / `na` placeholders.
    assert s.coilTemperature is None
    assert s.inducerRpm is None
    assert s.leavingAirTemperature is None
    assert s.pwmBlower is False
    assert s.lockoutActive is False
    # IDU lockouttime is a STRING (`"off"` when not locked); ODU has
    # an int locktime. Different field semantics — keep the raw text.
    assert s.lockoutTime == "off"


# ── End-to-end: POST → /v1/system/{odu,idu}_status ───────────────────


def test_post_odu_status_stores_and_serves_via_v1_endpoint():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    # 404 until first POST.
    assert client.get("/v1/system/odu_status").status_code == 404

    r = client.post(
        "/systems/2013W000855/odu_status",
        content=_read("odu_status_idle.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200

    body = client.get("/v1/system/odu_status").json()
    assert body["odutype"] == "hp2stgnoncomm"
    assert body["opstat"] == "Stage 0"
    assert body["operatingStage"] == 0
    assert body["outdoorTemperature"] == 72
    assert body["blowerRpm"] == 716
    assert body["compressorRpm"] is None  # idle
    assert body["lockoutActive"] is False


def test_post_idu_status_stores_and_serves_via_v1_endpoint():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    assert client.get("/v1/system/idu_status").status_code == 404

    r = client.post(
        "/systems/2013W000855/idu_status",
        content=_read("idu_status_idle.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200

    body = client.get("/v1/system/idu_status").json()
    assert body["idutype"] == "fancoilelectric"
    assert body["opstat"] == "off"
    assert body["operatingStage"] is None
    assert body["blowerRpm"] == 721
    assert body["coilTemperature"] is None  # `invalid` coerced
