"""Slice 6 — PATCH /v1/system/humidity.

Sparse update: write only the keys supplied. Parser already reads
targetHome/Away/Vacation (parser.py:_parse_humidity); this slice adds
the write path so users can tune per-mode target RH from the API.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_humidity_set
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

def test_apply_humidity_set_writes_all_three_targets():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_humidity_set(
        tree,
        {"targetHome": 40, "targetAway": 35, "targetVacation": 30},
    )
    assert _text(tree, "humidityHome") == "40"
    assert _text(tree, "humidityAway") == "35"
    assert _text(tree, "humidityVacation") == "30"


def test_apply_humidity_set_is_sparse():
    """Unsupplied keys must be left untouched — sparse PATCH semantic."""
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    # Prime with home=40 so we can verify it survives an away-only PATCH.
    apply_humidity_set(tree, {"targetHome": 40})
    apply_humidity_set(tree, {"targetAway": 35})
    assert _text(tree, "humidityHome") == "40"
    assert _text(tree, "humidityAway") == "35"


def test_apply_humidity_set_ignores_none_values():
    """Explicit None (unsupplied key in a dump) must not clobber an
    existing value — matches the endpoint's exclude_none semantics."""
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_humidity_set(tree, {"targetHome": 40})
    apply_humidity_set(
        tree, {"targetHome": None, "targetAway": 35, "targetVacation": None}
    )
    assert _text(tree, "humidityHome") == "40"
    assert _text(tree, "humidityAway") == "35"


# ── StateStore ────────────────────────────────────────────────────────

async def test_mutate_config_humidity_persists_and_enqueues():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_humidity_set,
        serial="0000TEST0000",
        kind="humidity_set",
        target="humidity",
        payload={"targetHome": 40, "targetAway": 35},
    )
    assert updated is not None
    assert updated.config.humidity.targetHome == 40
    assert updated.config.humidity.targetAway == 35

    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "humidity_set"
    assert store.config_dirty is True
    await p.close()


# ── HTTP ──────────────────────────────────────────────────────────────

def test_patch_humidity_updates_targets_and_echoes():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch(
        "/v1/system/humidity",
        json={"targetHome": 45, "targetAway": 35},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["targetHome"] == 45
    assert body["targetAway"] == 35
    # equipmentInstalled passes through from the stored config.
    assert body["equipmentInstalled"] is True


def test_patch_humidity_partial_leaves_others_alone():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Prime targetHome first, then tweak only targetAway.
    client.patch("/v1/system/humidity", json={"targetHome": 45})
    resp = client.patch("/v1/system/humidity", json={"targetAway": 30})
    assert resp.status_code == 200
    body = resp.json()
    assert body["targetHome"] == 45
    assert body["targetAway"] == 30


def test_patch_humidity_empty_body_422():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system/humidity", json={})
    assert resp.status_code == 422


def test_patch_humidity_out_of_range_422():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system/humidity", json={"targetHome": 150})
    assert resp.status_code == 422


def test_patch_humidity_rejects_extra_fields():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch(
        "/v1/system/humidity",
        json={"targetHome": 45, "equipmentInstalled": False},
    )
    assert resp.status_code == 422


def test_patch_humidity_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    resp = client.patch("/v1/system/humidity", json={"targetHome": 45})
    assert resp.status_code == 404


async def test_patch_humidity_with_persistence_enqueues_pending():
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
            r = client.patch(
                "/v1/system/humidity", json={"targetHome": 45}
            )
            assert r.status_code == 200
            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1
            assert pending[0].kind == "humidity_set"

            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay ────────────────────────────────────────────────────────────

async def test_replay_applies_humidity_onto_fresh_tree():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_humidity_set,
        serial="0000TEST0000",
        kind="humidity_set",
        target="humidity",
        payload={"targetHome": 45, "targetAway": 30},
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    stored = store.get_config()
    assert stored is not None
    assert _text(stored.tree, "humidityHome") == "45"
    assert _text(stored.tree, "humidityAway") == "30"
    assert store.config_dirty is True
    await p.close()
