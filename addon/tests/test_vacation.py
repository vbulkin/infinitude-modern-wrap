"""Slice 7 — PATCH /v1/system/vacation.

Sparse updates across: active on/off, start/end dates, vacation
setpoints, and fan. Parser has read all of these; this slice adds
the write path so vacation can be scheduled, re-targeted, or cancelled
from the northbound API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_vacation_set
from infinitude_proxy.parser import parse_system_config_with_tree
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _text(tree: etree._Element, tag: str) -> str:
    el = tree.find(tag)
    return (el.text or "") if el is not None else ""


# ── Mutation unit ─────────────────────────────────────────────────────

def test_apply_vacation_set_writes_all_fields():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_vacation_set(tree, {
        "active": True,
        "start": datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc),
        "end": datetime(2026, 7, 8, 17, 0, 0, tzinfo=timezone.utc),
        "heatSetpoint": 55,
        "coolSetpoint": 85,
        "fan": "low",
    })
    assert _text(tree, "vacat") == "on"
    assert _text(tree, "vacstart").startswith("2026-07-")
    assert _text(tree, "vacend").startswith("2026-07-")
    assert _text(tree, "vacmint") == "55.0"
    assert _text(tree, "vacmaxt") == "85.0"
    assert _text(tree, "vacfan") == "low"


def test_apply_vacation_set_is_sparse():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    # Fixture starts with vacat=off, vacmint=60.0, vacmaxt=80.0, vacfan=off.
    apply_vacation_set(tree, {"active": True})
    assert _text(tree, "vacat") == "on"
    # Unsupplied fields left alone.
    assert _text(tree, "vacmint") == "60.0"
    assert _text(tree, "vacfan") == "off"


def test_apply_vacation_set_disable_preserves_window():
    """Disabling via active=False must not touch vacstart/vacend — matches
    thermostat UX: disabling leaves the next-time window intact."""
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_vacation_set(tree, {
        "active": True,
        "start": datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc),
        "end": datetime(2026, 7, 8, 17, 0, 0, tzinfo=timezone.utc),
    })
    before_start = _text(tree, "vacstart")
    apply_vacation_set(tree, {"active": False})
    assert _text(tree, "vacat") == "off"
    assert _text(tree, "vacstart") == before_start


def test_apply_vacation_set_accepts_iso_strings():
    """Replay feeds the payload back from JSON — start/end arrive as
    strings, not datetimes. Mutation must accept both."""
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_vacation_set(tree, {
        "start": "2026-07-01T08:00:00+00:00",
        "end": "2026-07-08T17:00:00+00:00",
    })
    assert _text(tree, "vacstart").startswith("2026-07-01")
    assert _text(tree, "vacend").startswith("2026-07-08")


# ── StateStore ────────────────────────────────────────────────────────

async def test_mutate_config_vacation_persists_and_enqueues():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_vacation_set,
        serial="0000TEST0000",
        kind="vacation_set",
        target="vacation",
        payload={"active": True, "heatSetpoint": 55, "coolSetpoint": 85},
    )
    assert updated is not None
    assert updated.config.vacation.active is True
    assert updated.config.vacation.heatSetpoint == 55
    assert updated.config.vacation.coolSetpoint == 85

    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "vacation_set"
    assert store.config_dirty is True
    await p.close()


# ── HTTP ──────────────────────────────────────────────────────────────

def test_patch_vacation_schedules_window_and_echoes():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system/vacation", json={
        "active": True,
        "start": "2026-07-01T08:00:00Z",
        "end": "2026-07-08T17:00:00Z",
        "heatSetpoint": 55,
        "coolSetpoint": 85,
        "fan": "low",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["heatSetpoint"] == 55
    assert body["coolSetpoint"] == 85
    assert body["fan"] == "low"


def test_patch_vacation_partial_active_only():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system/vacation", json={"active": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    # Fixture defaults preserved.
    assert body["heatSetpoint"] == 60
    assert body["coolSetpoint"] == 80


def test_patch_vacation_empty_body_422():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system/vacation", json={})
    assert resp.status_code == 422


def test_patch_vacation_setpoint_out_of_range_422():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system/vacation", json={"heatSetpoint": 120})
    assert resp.status_code == 422


def test_patch_vacation_rejects_extra_fields():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch(
        "/v1/system/vacation", json={"active": True, "pets": "cat"}
    )
    assert resp.status_code == 422


def test_patch_vacation_rejects_invalid_fan():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system/vacation", json={"fan": "turbo"})
    assert resp.status_code == 422


def test_patch_vacation_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    resp = client.patch("/v1/system/vacation", json={"active": True})
    assert resp.status_code == 404


async def test_patch_vacation_with_persistence_enqueues_pending():
    p = await Persistence.open(":memory:")
    try:
        store = StateStore(persistence=p)
        app = create_app(store=store)
        with TestClient(app) as client:
            client.post(
                "/systems/0000TEST0000",
                content=_read("boot_01_system_config.xml"),
                headers={"content-type": "application/xml"},
            )
            r = client.patch("/v1/system/vacation", json={"active": True})
            assert r.status_code == 200
            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1
            assert pending[0].kind == "vacation_set"

            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay ────────────────────────────────────────────────────────────

async def test_replay_applies_vacation_onto_fresh_tree():
    """Reboot race: a pending vacation_set (with date strings stored in
    the payload JSON) must re-apply cleanly onto a fresh tree."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_vacation_set,
        serial="0000TEST0000",
        kind="vacation_set",
        target="vacation",
        payload={
            "active": True,
            "start": "2026-07-01T08:00:00+00:00",
            "end": "2026-07-08T17:00:00+00:00",
            "heatSetpoint": 55,
            "coolSetpoint": 85,
        },
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    stored = store.get_config()
    assert stored is not None
    assert _text(stored.tree, "vacat") == "on"
    assert _text(stored.tree, "vacmint") == "55.0"
    assert _text(stored.tree, "vacmaxt") == "85.0"
    assert store.config_dirty is True
    await p.close()
