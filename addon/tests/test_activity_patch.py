"""Slice 9 — PATCH /v1/zones/{id}/activities/{id}.

Sparse update of any activity's heat/cool/fan without engaging a hold.
Distinct from PATCH /v1/zones/{id}, which edits the `manual` activity
AND flips hold=on/holdActivity=manual to force immediate effect.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_activity_set
from infinitude_proxy.parser import parse_system_config_with_tree
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _activity_text(tree: etree._Element, zone_id: str, activity_id: str, tag: str) -> str:
    zone = next(
        z for z in tree.find("zones").findall("zone") if z.get("id") == zone_id
    )
    act = next(
        a for a in zone.find("activities").findall("activity")
        if a.get("id") == activity_id
    )
    el = act.find(tag)
    return (el.text or "") if el is not None else ""


# ── Mutation unit ─────────────────────────────────────────────────────

def test_apply_activity_set_writes_all_fields():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_activity_set(tree, {
        "zone_id": "1",
        "activity_id": "home",
        "heat": 70,
        "cool": 72,
        "fan": "med",
    })
    assert _activity_text(tree, "1", "home", "htsp") == "70.0"
    assert _activity_text(tree, "1", "home", "clsp") == "72.0"
    assert _activity_text(tree, "1", "home", "fan") == "med"


def test_apply_activity_set_is_sparse():
    """Unsupplied fields are left alone."""
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    original_cool = _activity_text(tree, "1", "home", "clsp")
    original_fan = _activity_text(tree, "1", "home", "fan")
    apply_activity_set(tree, {"zone_id": "1", "activity_id": "home", "heat": 69})
    assert _activity_text(tree, "1", "home", "htsp") == "69.0"
    assert _activity_text(tree, "1", "home", "clsp") == original_cool
    assert _activity_text(tree, "1", "home", "fan") == original_fan


def test_apply_activity_set_does_not_touch_hold():
    """Editing an activity must leave hold state untouched — the whole
    point of this mutation vs apply_zone_setpoints_set."""
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    zone = next(
        z for z in tree.find("zones").findall("zone") if z.get("id") == "1"
    )
    before_hold = (zone.find("hold").text or "") if zone.find("hold") is not None else ""
    apply_activity_set(tree, {
        "zone_id": "1", "activity_id": "home", "heat": 70, "cool": 72
    })
    after_hold = (zone.find("hold").text or "") if zone.find("hold") is not None else ""
    assert after_hold == before_hold


def test_apply_activity_set_unknown_activity_raises():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    try:
        apply_activity_set(tree, {
            "zone_id": "1", "activity_id": "nonesuch", "heat": 70
        })
    except ValueError as e:
        assert "nonesuch" in str(e)
    else:
        raise AssertionError("expected ValueError for unknown activity")


# ── StateStore ────────────────────────────────────────────────────────

async def test_mutate_config_activity_persists_and_enqueues():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_activity_set,
        serial="0000TEST0000",
        kind="activity_set",
        target="zone:1:activity:home",
        payload={"zone_id": "1", "activity_id": "home", "heat": 69, "cool": 73},
    )
    assert updated is not None
    home = next(
        a for a in updated.config.zones[0].activities if a.id == "home"
    )
    assert home.heat == 69
    assert home.cool == 73

    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "activity_set"
    assert store.config_dirty is True
    await p.close()


# ── HTTP ──────────────────────────────────────────────────────────────

def _seed_client() -> TestClient:
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    return client


def test_patch_activity_updates_all_fields_and_echoes():
    client = _seed_client()
    resp = client.patch(
        "/v1/zones/1/activities/home",
        json={"heat": 70, "cool": 72, "fan": "med"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "home"
    assert body["heat"] == 70
    assert body["cool"] == 72
    assert body["fan"] == "med"


def test_patch_activity_partial_heat_only():
    client = _seed_client()
    resp = client.patch("/v1/zones/1/activities/sleep", json={"heat": 67})
    assert resp.status_code == 200
    body = resp.json()
    assert body["heat"] == 67
    # sleep.cool started at 76 in the fixture; unchanged.
    assert body["cool"] == 76


def test_patch_activity_empty_body_422():
    client = _seed_client()
    resp = client.patch("/v1/zones/1/activities/home", json={})
    assert resp.status_code == 422


def test_patch_activity_rejects_extra_fields():
    client = _seed_client()
    resp = client.patch(
        "/v1/zones/1/activities/home",
        json={"heat": 68, "activateHold": True},
    )
    assert resp.status_code == 422


def test_patch_activity_rejects_out_of_range_setpoint():
    client = _seed_client()
    resp = client.patch("/v1/zones/1/activities/home", json={"heat": 120})
    assert resp.status_code == 422


def test_patch_activity_rejects_invalid_fan():
    client = _seed_client()
    resp = client.patch(
        "/v1/zones/1/activities/home", json={"fan": "turbo"}
    )
    assert resp.status_code == 422


def test_patch_activity_unknown_zone_404():
    client = _seed_client()
    resp = client.patch("/v1/zones/99/activities/home", json={"heat": 70})
    assert resp.status_code == 404


def test_patch_activity_unknown_activity_404():
    client = _seed_client()
    resp = client.patch(
        "/v1/zones/1/activities/nonesuch", json={"heat": 70}
    )
    assert resp.status_code == 404


def test_patch_activity_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    resp = client.patch("/v1/zones/1/activities/home", json={"heat": 70})
    assert resp.status_code == 404


async def test_patch_activity_with_persistence_enqueues_pending():
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
                "/v1/zones/1/activities/home", json={"heat": 70}
            )
            assert r.status_code == 200
            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1
            assert pending[0].kind == "activity_set"

            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay ────────────────────────────────────────────────────────────

async def test_replay_applies_activity_onto_fresh_tree():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_activity_set,
        serial="0000TEST0000",
        kind="activity_set",
        target="zone:1:activity:home",
        payload={"zone_id": "1", "activity_id": "home", "heat": 70, "cool": 72},
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    stored = store.get_config()
    assert stored is not None
    assert _activity_text(stored.tree, "1", "home", "htsp") == "70.0"
    assert _activity_text(stored.tree, "1", "home", "clsp") == "72.0"
    assert store.config_dirty is True
    await p.close()
