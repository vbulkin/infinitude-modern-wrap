"""Slice 4 — GET /v1/system + PATCH /v1/system (mode).

Unit (mutation), store (mutate_config), HTTP (GET + PATCH), replay.
Mode changes are a single-element edit — simpler than hold, but exercise
the same REPLAY_REGISTRY path so a pending mode switch survives reboot.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_system_mode_set
from infinitude_proxy.parser import parse_system_config_with_tree
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _mode(tree: etree._Element) -> str:
    el = tree.find("mode")
    return (el.text or "") if el is not None else ""


# ── Mutation unit ─────────────────────────────────────────────────────

def test_apply_system_mode_set_writes_mode_text():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_system_mode_set(tree, {"mode": "heat"})
    assert _mode(tree) == "heat"


def test_apply_system_mode_set_overwrites_existing():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    # Fixture starts with mode=cool; flip to off.
    assert _mode(tree) == "cool"
    apply_system_mode_set(tree, {"mode": "off"})
    assert _mode(tree) == "off"


def test_apply_system_mode_set_creates_missing_element():
    # Partial fixtures without <mode> should still accept the write.
    tree = etree.fromstring(b"<config><zones/><wholeHouse/></config>")
    apply_system_mode_set(tree, {"mode": "auto"})
    assert tree.find("mode").text == "auto"


# ── StateStore.mutate_config ──────────────────────────────────────────

async def test_mutate_config_system_mode_persists_and_enqueues():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_system_mode_set,
        serial="0000TEST0000",
        kind="system_mode_set",
        target="system",
        payload={"mode": "heat"},
    )
    assert updated is not None
    assert updated.config.mode == "heat"
    assert _mode(updated.tree) == "heat"

    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "system_mode_set"
    assert pending[0].payload == {"mode": "heat"}
    assert store.config_dirty is True
    await p.close()


# ── HTTP endpoints ────────────────────────────────────────────────────

def test_get_system_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    resp = client.get("/v1/system")
    assert resp.status_code == 404


def test_get_system_returns_snapshot():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.get("/v1/system")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "cool"
    assert body["serial"] == "0000TEST0000"
    assert body["hold"]["active"] is False


def test_patch_system_mode_mutates_and_signals_dirty():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system", json={"mode": "heat"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "heat"

    # Tree reflects the write.
    cfg = client.get("/systems/0000TEST0000/config").content
    root = etree.fromstring(cfg)
    assert root.find("mode").text == "heat"

    # Directive channel signals dirty on next status POST.
    status_resp = client.post(
        "/systems/0000TEST0000/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert status_resp.status_code == 200
    assert b"<configHasChanges>true</configHasChanges>" in status_resp.content


def test_patch_system_rejects_empty_body():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system", json={})
    assert resp.status_code == 422


def test_patch_system_rejects_invalid_mode():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system", json={"mode": "bogus"})
    assert resp.status_code == 422


def test_patch_system_rejects_extra_fields():
    """SystemPatch has extra='forbid' — unknown keys must 422."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch(
        "/v1/system", json={"mode": "heat", "serial": "hijack"}
    )
    assert resp.status_code == 422


def test_patch_system_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    resp = client.patch("/v1/system", json={"mode": "heat"})
    assert resp.status_code == 404


async def test_patch_system_with_persistence_enqueues_pending():
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
            r = client.patch("/v1/system", json={"mode": "heat"})
            assert r.status_code == 200

            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1
            assert pending[0].kind == "system_mode_set"

            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay dispatcher ─────────────────────────────────────────────────

async def test_replay_applies_system_mode_onto_fresh_tree():
    """Reboot race: pending system_mode_set must re-apply when the
    thermostat posts a fresh (stale) config."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_system_mode_set,
        serial="0000TEST0000",
        kind="system_mode_set",
        target="system",
        payload={"mode": "heat"},
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    stored = store.get_config()
    assert stored is not None
    assert _mode(stored.tree) == "heat"
    assert stored.config.mode == "heat"
    assert await p.unapplied_count("0000TEST0000") == 1
    assert store.config_dirty is True
    await p.close()
