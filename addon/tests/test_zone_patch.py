"""Slice 5 — GET /v1/zones, GET/PATCH /v1/zones/{id} (manual setpoints).

PATCH /v1/zones/{id} writes heat/cool into the zone's `manual` activity
and — unless `activateHold=false` — flips the zone into manual hold so
the new setpoints take effect immediately. Composite mutation: activity
edit + hold engage, stored as a single `zone_setpoints_set` pending row
so replay is atomic.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_zone_setpoints_set
from infinitude_proxy.parser import parse_system_config_with_tree
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _zone_elem(tree: etree._Element, zone_id: str) -> etree._Element:
    return next(
        z for z in tree.find("zones").findall("zone") if z.get("id") == zone_id
    )


def _manual(zone: etree._Element) -> etree._Element:
    return next(
        a for a in zone.find("activities").findall("activity")
        if a.get("id") == "manual"
    )


def _text(el: etree._Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "") if child is not None else ""


# ── Mutation unit ─────────────────────────────────────────────────────

def test_apply_zone_setpoints_set_writes_both_and_engages_hold():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_zone_setpoints_set(
        tree,
        {"zone_id": "1", "heat": 70, "cool": 74, "activate_hold": True},
    )
    z1 = _zone_elem(tree, "1")
    m = _manual(z1)
    assert _text(m, "htsp") == "70.0"
    assert _text(m, "clsp") == "74.0"
    assert _text(z1, "hold") == "on"
    assert _text(z1, "holdActivity") == "manual"
    assert _text(z1, "otmr") == ""


def test_apply_zone_setpoints_set_heat_only_leaves_cool_alone():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    # Fixture's manual cool starts at 76.0 — heat-only PATCH must not clobber it.
    apply_zone_setpoints_set(
        tree,
        {"zone_id": "1", "heat": 65, "cool": None, "activate_hold": True},
    )
    m = _manual(_zone_elem(tree, "1"))
    assert _text(m, "htsp") == "65.0"
    assert _text(m, "clsp") == "76.0"


def test_apply_zone_setpoints_set_without_hold_leaves_hold_unchanged():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    # Fixture zone 1 starts with hold=off. activate_hold=False must not flip.
    apply_zone_setpoints_set(
        tree,
        {"zone_id": "1", "heat": 70, "cool": 74, "activate_hold": False},
    )
    z1 = _zone_elem(tree, "1")
    assert _text(z1, "hold") == "off"
    m = _manual(z1)
    assert _text(m, "htsp") == "70.0"
    assert _text(m, "clsp") == "74.0"


def test_apply_zone_setpoints_set_unknown_zone_raises():
    import pytest
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    with pytest.raises(ValueError, match="zone 99 not found"):
        apply_zone_setpoints_set(
            tree,
            {"zone_id": "99", "heat": 70, "cool": 74, "activate_hold": True},
        )


# ── StateStore.mutate_config ──────────────────────────────────────────

async def test_mutate_config_zone_setpoints_persists_and_enqueues():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_zone_setpoints_set,
        serial="0000TEST0000",
        kind="zone_setpoints_set",
        target="zone:1",
        payload={
            "zone_id": "1", "heat": 70, "cool": 74, "activate_hold": True,
        },
    )
    assert updated is not None

    z1 = next(z for z in updated.config.zones if z.id == "1")
    manual_activity = next(a for a in z1.activities if a.id == "manual")
    assert manual_activity.heat == 70
    assert manual_activity.cool == 74
    assert z1.hold.active is True
    assert z1.hold.activity == "manual"

    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "zone_setpoints_set"
    assert pending[0].payload["heat"] == 70
    assert store.config_dirty is True
    await p.close()


# ── HTTP: GET /v1/zones and GET /v1/zones/{id} ────────────────────────

def test_list_zones_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    resp = client.get("/v1/zones")
    assert resp.status_code == 404


def test_list_zones_returns_all_zones():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.get("/v1/zones")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Fixture has 8 zones; spec says include disabled, so count matches raw XML.
    ids = [z["id"] for z in body]
    assert "1" in ids
    assert len(ids) >= 1


def test_get_zone_returns_single_zone():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.get("/v1/zones/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == "1"


def test_get_zone_unknown_zone_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.get("/v1/zones/99")
    assert resp.status_code == 404


# ── HTTP: PATCH /v1/zones/{id} ────────────────────────────────────────

def test_patch_zone_sets_manual_setpoints_and_holds():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/zones/1", json={"heat": 70, "cool": 74})
    assert resp.status_code == 200
    body = resp.json()
    assert body["hold"]["active"] is True
    assert body["hold"]["activity"] == "manual"
    # Response echoes the hold-target setpoints (config is authoritative
    # while telemetry still reflects the prior activity).
    assert body["heatSetpoint"] == 70
    assert body["coolSetpoint"] == 74

    cfg = client.get("/systems/0000TEST0000/config").content
    root = etree.fromstring(cfg)
    z1 = next(z for z in root.find("zones").findall("zone") if z.get("id") == "1")
    m = _manual(z1)
    assert _text(m, "htsp") == "70.0"
    assert _text(m, "clsp") == "74.0"
    assert _text(z1, "hold") == "on"


def test_state_echoes_held_setpoints_after_patch_with_telemetry():
    """`/v1/state` must echo the held-activity setpoints right after a
    PATCH, even with stale telemetry on file. This is the "user bumped
    the temperature, UI snapped back to the old value for ~30 s"
    regression — telemetry's last-reported heatSetpoint reflects the
    activity that *was* active before the write, not the manual hold
    we just engaged.
    """
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Seed telemetry so the response merges config + telemetry — this is
    # the live-install shape, where telemetry exists and otherwise wins.
    client.post(
        "/systems/0000TEST0000/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    # Bump heat to 70 and engage manual hold (default behavior).
    client.patch("/v1/zones/1", json={"heat": 70, "cool": 74})
    # Edit the manual activity's fan independently. The held-activity
    # fan should win in the next /v1/state read just like setpoints.
    client.patch(
        "/v1/zones/1/activities/manual", json={"fan": "high"}
    )

    state = client.get("/v1/state")
    assert state.status_code == 200
    z1 = next(z for z in state.json()["zones"] if z["id"] == "1")
    # Held setpoints from config beat stale telemetry. Without the
    # _build_zone hold-aware merge this would be telemetry's pre-write
    # heat value (68 in the boot fixture).
    assert z1["heatSetpoint"] == 70
    assert z1["coolSetpoint"] == 74
    assert z1["fan"] == "high"
    assert z1["hold"]["activity"] == "manual"
    assert z1["currentActivity"] == "manual"


def test_patch_zone_without_activate_hold_stages_setpoints():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch(
        "/v1/zones/1",
        json={"heat": 70, "cool": 74, "activateHold": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["hold"]["active"] is False

    cfg = client.get("/systems/0000TEST0000/config").content
    root = etree.fromstring(cfg)
    z1 = next(z for z in root.find("zones").findall("zone") if z.get("id") == "1")
    m = _manual(z1)
    assert _text(m, "htsp") == "70.0"
    assert _text(z1, "hold") == "off"


def test_patch_zone_heat_only():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/zones/1", json={"heat": 65})
    assert resp.status_code == 200

    cfg = client.get("/systems/0000TEST0000/config").content
    root = etree.fromstring(cfg)
    m = _manual(next(
        z for z in root.find("zones").findall("zone") if z.get("id") == "1"
    ))
    assert _text(m, "htsp") == "65.0"
    # Manual cool was 76.0 in the fixture; heat-only PATCH leaves it alone.
    assert _text(m, "clsp") == "76.0"


def test_patch_zone_empty_body_422():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/zones/1", json={})
    assert resp.status_code == 422


def test_patch_zone_out_of_range_422():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Temperature is bounded [45, 99] — 120 must fail at pydantic boundary.
    resp = client.patch("/v1/zones/1", json={"heat": 120})
    assert resp.status_code == 422


def test_patch_zone_rejects_extra_fields():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/zones/1", json={"heat": 70, "fan": "high"})
    assert resp.status_code == 422


def test_patch_zone_unknown_zone_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/zones/99", json={"heat": 70})
    assert resp.status_code == 404


def test_patch_zone_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    resp = client.patch("/v1/zones/1", json={"heat": 70})
    assert resp.status_code == 404


async def test_patch_zone_with_persistence_enqueues_pending():
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
            r = client.patch("/v1/zones/1", json={"heat": 70, "cool": 74})
            assert r.status_code == 200

            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1
            assert pending[0].kind == "zone_setpoints_set"

            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay dispatcher ─────────────────────────────────────────────────

async def test_replay_applies_zone_setpoints_onto_fresh_tree():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_zone_setpoints_set,
        serial="0000TEST0000",
        kind="zone_setpoints_set",
        target="zone:1",
        payload={
            "zone_id": "1", "heat": 70, "cool": 74, "activate_hold": True,
        },
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    # Thermostat reboot simulation — fresh tree (no mutation) replayed.
    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    stored = store.get_config()
    assert stored is not None
    z1_el = _zone_elem(stored.tree, "1")
    m = _manual(z1_el)
    assert _text(m, "htsp") == "70.0"
    assert _text(m, "clsp") == "74.0"
    assert _text(z1_el, "hold") == "on"
    assert store.config_dirty is True
    assert await p.unapplied_count("0000TEST0000") == 1
    await p.close()
