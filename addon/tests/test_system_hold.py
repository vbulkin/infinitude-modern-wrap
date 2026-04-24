"""Slice 3 — whole-house hold PUT/DELETE /v1/system/hold.

Mirror of test_zone_hold but scoped to the <wholeHouse> subtree: the
same <hold>/<holdActivity>/<otmr> trio, a narrower activity enum (no
"manual"), and a System response rather than a Zone response.

Layers covered — unit (mutation), store (mutate_config), HTTP, replay.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import (
    apply_system_hold_clear,
    apply_system_hold_set,
)
from infinitude_proxy.parser import parse_system_config_with_tree
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _wh(tree: etree._Element) -> etree._Element:
    wh = tree.find("wholeHouse")
    assert wh is not None
    return wh


def _text(el: etree._Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "") if child is not None else ""


# ── Tree edits ────────────────────────────────────────────────────────

def test_apply_system_hold_set_writes_all_three_fields():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_system_hold_set(tree, {"activity": "home", "otmr": "14:45"})
    wh = _wh(tree)
    assert _text(wh, "hold") == "on"
    assert _text(wh, "holdActivity") == "home"
    assert _text(wh, "otmr") == "14:45"


def test_apply_system_hold_set_hold_forever_leaves_otmr_empty():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_system_hold_set(tree, {"activity": "away", "otmr": ""})
    wh = _wh(tree)
    assert _text(wh, "hold") == "on"
    assert _text(wh, "holdActivity") == "away"
    assert _text(wh, "otmr") == ""


def test_apply_system_hold_clear_wipes_fields():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_system_hold_set(tree, {"activity": "home", "otmr": "16:00"})
    apply_system_hold_clear(tree, {})
    wh = _wh(tree)
    assert _text(wh, "hold") == "off"
    assert _text(wh, "holdActivity") == "none"
    assert _text(wh, "otmr") == ""


def test_apply_system_hold_set_missing_whole_house_raises():
    import pytest
    # Fabricate a config without <wholeHouse> — asserts the guard.
    tree = etree.fromstring(b"<config><zones/></config>")
    with pytest.raises(ValueError, match="wholeHouse"):
        apply_system_hold_set(tree, {"activity": "home", "otmr": ""})


# ── StateStore.mutate_config ──────────────────────────────────────────

async def test_mutate_config_system_hold_persists_and_enqueues():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_system_hold_set,
        serial="0000TEST0000",
        kind="system_hold_set",
        target="system",
        payload={"activity": "home", "otmr": "14:45"},
    )
    assert updated is not None
    assert updated.config.wholeHouseHold.active is True
    assert updated.config.wholeHouseHold.activity == "home"

    wh = _wh(updated.tree)
    assert _text(wh, "hold") == "on"
    assert _text(wh, "otmr") == "14:45"

    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "system_hold_set"
    assert pending[0].target == "system"
    assert pending[0].payload == {"activity": "home", "otmr": "14:45"}
    assert store.config_dirty is True
    await p.close()


# ── HTTP endpoints ────────────────────────────────────────────────────

def test_put_system_hold_mutates_config_and_signals_dirty():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    resp = client.put(
        "/v1/system/hold",
        json={"activity": "home", "until": "16:00"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["hold"]["active"] is True
    assert body["hold"]["activity"] == "home"
    assert body["hold"]["until"] == "16:00"

    cfg_resp = client.get("/systems/0000TEST0000/config")
    assert cfg_resp.status_code == 200
    root = etree.fromstring(cfg_resp.content)
    wh = root.find("wholeHouse")
    assert _text(wh, "hold") == "on"
    assert _text(wh, "holdActivity") == "home"

    # Dirty flag routed through directive channel on next status POST.
    status_resp = client.post(
        "/systems/0000TEST0000/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert status_resp.status_code == 200
    assert b"<configHasChanges>true</configHasChanges>" in status_resp.content


def test_put_system_hold_forever_sends_empty_otmr():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.put("/v1/system/hold", json={"activity": "away"})
    assert resp.status_code == 200

    cfg = client.get("/systems/0000TEST0000/config").content
    root = etree.fromstring(cfg)
    wh = root.find("wholeHouse")
    otmr = wh.find("otmr")
    assert otmr is not None
    assert not (otmr.text or "")


def test_put_system_hold_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    resp = client.put("/v1/system/hold", json={"activity": "home"})
    assert resp.status_code == 404


def test_put_system_hold_rejects_manual_activity():
    """SystemHoldActivity is narrower than ActivityId — manual is not valid."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.put("/v1/system/hold", json={"activity": "manual"})
    assert resp.status_code == 422


def test_delete_system_hold_clears_fields():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    client.put("/v1/system/hold", json={"activity": "home"})
    resp = client.delete("/v1/system/hold")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hold"]["active"] is False
    assert body["hold"]["activity"] is None


def test_delete_system_hold_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    resp = client.delete("/v1/system/hold")
    assert resp.status_code == 404


async def test_put_system_hold_with_persistence_enqueues_pending():
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
            r = client.put("/v1/system/hold", json={"activity": "home"})
            assert r.status_code == 200
            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1
            assert pending[0].kind == "system_hold_set"

            # Pull-observed clear on next GET /config.
            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay dispatcher ─────────────────────────────────────────────────

async def test_replay_applies_system_hold_onto_fresh_tree():
    """Reboot race: pending system_hold_set must be re-applied when the
    thermostat posts a fresh (stale) config tree."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_system_hold_set,
        serial="0000TEST0000",
        kind="system_hold_set",
        target="system",
        payload={"activity": "home", "otmr": "14:45"},
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    stored = store.get_config()
    assert stored is not None
    wh = _wh(stored.tree)
    assert _text(wh, "hold") == "on"
    assert _text(wh, "holdActivity") == "home"
    assert stored.config.wholeHouseHold.active is True
    # Pending still unapplied until pull — see pull-observed clear semantic.
    assert await p.unapplied_count("0000TEST0000") == 1
    assert store.config_dirty is True
    await p.close()
