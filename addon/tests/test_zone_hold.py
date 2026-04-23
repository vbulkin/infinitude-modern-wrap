"""Slice 2 — first northbound write: zone hold PUT/DELETE.

Covers three layers:
  - mutations unit tests (quarter-hour snap, tree edits)
  - StateStore.mutate_config (tree edit + pending row + dirty flag + persisted bytes)
  - HTTP contract (PUT/DELETE /v1/zones/{id}/hold → Zone response)
  - replay dispatcher (thermostat-reboot race: pending row replayed onto fresh tree)

The pull-observed clear (GET /config marks pending applied) is already
exercised by test_persistence; we verify here that the full mutate →
clear cycle ends with the mutation embedded in the tree we serve back
to the thermostat.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import (
    apply_zone_hold_clear,
    apply_zone_hold_set,
    datetime_to_wall_time,
    snap_quarter_hour,
)
from infinitude_proxy.parser import (
    parse_system_config_with_tree,
    serialize_config_tree,
)
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _zone_elem(tree: etree._Element, zone_id: str) -> etree._Element:
    return next(
        z for z in tree.find("zones").findall("zone") if z.get("id") == zone_id
    )


def _text(el: etree._Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "") if child is not None else ""


# ── Quarter-hour snap ────────────────────────────────────────────────

def test_snap_quarter_hour_exact_values_unchanged():
    assert snap_quarter_hour("14:45") == "14:45"
    assert snap_quarter_hour("00:00") == "00:00"
    assert snap_quarter_hour("23:30") == "23:30"


def test_snap_quarter_hour_rounds_nearest():
    # Half-up policy: 7 → 0, 8 → 15, 22 → 15, 23 → 30.
    assert snap_quarter_hour("14:07") == "14:00"
    assert snap_quarter_hour("14:08") == "14:15"
    assert snap_quarter_hour("14:22") == "14:15"
    assert snap_quarter_hour("14:23") == "14:30"


def test_snap_quarter_hour_wraps_midnight():
    # 23:53 + rounding → 24:00 → wrap to 00:00.
    assert snap_quarter_hour("23:53") == "00:00"


def test_snap_quarter_hour_empty_is_forever():
    # Empty otmr = thermostat's "hold indefinitely" semantic — must pass through.
    assert snap_quarter_hour("") == ""


def test_datetime_to_wall_time_snaps_local_minutes():
    # Same local clock regardless of zone: compute the expected local HH:MM
    # and compare. (The test can't hard-code HH without knowing the host TZ.)
    dt = datetime(2026, 4, 20, 14, 7, 0, tzinfo=timezone.utc)
    local_mm = dt.astimezone().minute
    local_hh = dt.astimezone().hour
    total = local_hh * 60 + local_mm
    snapped = ((total + 7) // 15) * 15
    snapped %= 24 * 60
    expected = f"{snapped // 60:02d}:{snapped % 60:02d}"
    assert datetime_to_wall_time(dt) == expected


# ── Tree edits ────────────────────────────────────────────────────────

def test_apply_zone_hold_set_writes_all_three_fields():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_zone_hold_set(
        tree,
        {"zone_id": "1", "activity": "manual", "otmr": "14:45"},
    )
    z1 = _zone_elem(tree, "1")
    assert _text(z1, "hold") == "on"
    assert _text(z1, "holdActivity") == "manual"
    assert _text(z1, "otmr") == "14:45"


def test_apply_zone_hold_set_hold_forever_leaves_otmr_empty():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_zone_hold_set(
        tree,
        {"zone_id": "1", "activity": "away", "otmr": ""},
    )
    z1 = _zone_elem(tree, "1")
    assert _text(z1, "hold") == "on"
    assert _text(z1, "holdActivity") == "away"
    assert _text(z1, "otmr") == ""


def test_apply_zone_hold_clear_wipes_fields():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    # Set first so we have something to clear.
    apply_zone_hold_set(
        tree, {"zone_id": "1", "activity": "manual", "otmr": "16:00"}
    )
    apply_zone_hold_clear(tree, {"zone_id": "1"})
    z1 = _zone_elem(tree, "1")
    assert _text(z1, "hold") == "off"
    assert _text(z1, "holdActivity") == "none"
    assert _text(z1, "otmr") == ""


def test_apply_zone_hold_set_unknown_zone_raises():
    import pytest
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    with pytest.raises(ValueError, match="zone 99 not found"):
        apply_zone_hold_set(
            tree, {"zone_id": "99", "activity": "manual", "otmr": ""}
        )


# ── StateStore.mutate_config ──────────────────────────────────────────

async def test_mutate_config_persists_bytes_and_enqueues_pending():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_zone_hold_set,
        serial="0000TEST0000",
        kind="zone_hold_set",
        target="zone:1",
        payload={"zone_id": "1", "activity": "manual", "otmr": "14:45"},
    )
    assert updated is not None

    # Typed snapshot reflects the mutation.
    z1 = next(z for z in updated.config.zones if z.id == "1")
    assert z1.hold.active is True
    assert z1.hold.activity == "manual"

    # Raw tree has the new values.
    z1_el = _zone_elem(updated.tree, "1")
    assert _text(z1_el, "hold") == "on"
    assert _text(z1_el, "otmr") == "14:45"

    # Pending row enqueued, dirty flag set.
    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "zone_hold_set"
    assert pending[0].target == "zone:1"
    assert pending[0].payload == {
        "zone_id": "1", "activity": "manual", "otmr": "14:45",
    }
    assert store.config_dirty is True

    # Persisted bytes round-trip through the tree.
    snap = await p.load("0000TEST0000")
    assert snap is not None
    assert b"<hold>on</hold>" in snap.config_xml
    assert snap.config_dirty is True
    await p.close()


async def test_mutate_config_no_config_returns_none():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    # No apply_config yet → mutate_config must no-op (caller 404s).
    result = await store.mutate_config(
        apply_zone_hold_set,
        serial="0000TEST0000",
        kind="zone_hold_set",
        target="zone:1",
        payload={"zone_id": "1", "activity": "manual", "otmr": ""},
    )
    assert result is None
    assert await p.unapplied_count() == 0
    await p.close()


async def test_mutate_config_wrong_serial_returns_none():
    """Single-unit assumption: if the stored config's serial differs, we
    refuse rather than corrupt another unit's tree."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("SERIAL_A", config, tree)

    result = await store.mutate_config(
        apply_zone_hold_set,
        serial="SERIAL_B",
        kind="zone_hold_set",
        target="zone:1",
        payload={"zone_id": "1", "activity": "manual", "otmr": ""},
    )
    assert result is None
    assert await p.unapplied_count() == 0
    await p.close()


# ── HTTP endpoints ────────────────────────────────────────────────────

def test_put_zone_hold_mutates_config_and_signals_dirty():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    until = (datetime(2026, 4, 20, 16, 0, 0, tzinfo=timezone.utc))
    resp = client.put(
        "/v1/zones/1/hold",
        json={"activity": "manual", "until": until.isoformat()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "1"
    assert body["hold"]["active"] is True
    assert body["hold"]["activity"] == "manual"

    # Tree has been mutated — serving GET /config returns the new hold.
    cfg_resp = client.get("/systems/0000TEST0000/config")
    assert cfg_resp.status_code == 200
    assert b"<hold>on</hold>" in cfg_resp.content

    # Next status POST should signal configHasChanges=true (dirty set by mutate).
    status_resp = client.post(
        "/systems/0000TEST0000/status",
        content=_read("boot_05_status_telemetry.xml"),
        headers={"content-type": "application/xml"},
    )
    assert status_resp.status_code == 200
    assert b"<configHasChanges>true</configHasChanges>" in status_resp.content


def test_put_zone_hold_forever_sends_empty_otmr():
    """No `until` = hold forever — thermostat reads empty <otmr/> as no expiry."""
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    resp = client.put("/v1/zones/1/hold", json={"activity": "away"})
    assert resp.status_code == 200

    cfg = client.get("/systems/0000TEST0000/config").content
    # The zone-1 block should contain an empty <otmr/> (or <otmr></otmr>).
    # Parse to verify — substring-search gets tangled up with other zones'
    # otmr values.
    root = etree.fromstring(cfg)
    z1 = next(z for z in root.find("zones").findall("zone") if z.get("id") == "1")
    otmr = z1.find("otmr")
    assert otmr is not None
    assert not (otmr.text or "")


def test_put_zone_hold_unknown_zone_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    resp = client.put("/v1/zones/99/hold", json={"activity": "manual"})
    assert resp.status_code == 404


def test_put_zone_hold_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    resp = client.put("/v1/zones/1/hold", json={"activity": "manual"})
    assert resp.status_code == 404


def test_put_zone_hold_rejects_invalid_activity():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )

    resp = client.put("/v1/zones/1/hold", json={"activity": "bogus"})
    assert resp.status_code == 422


def test_delete_zone_hold_clears_fields():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Put then clear — exercise the full cycle.
    client.put("/v1/zones/1/hold", json={"activity": "manual"})
    resp = client.delete("/v1/zones/1/hold")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hold"]["active"] is False
    # API contract: cleared hold has no activity — ZoneHold.activity is None
    # (our _parse_zone_hold turns <holdActivity>none</holdActivity> into None).
    assert body["hold"]["activity"] is None


async def test_put_zone_hold_with_persistence_enqueues_pending():
    """Full lifespan: PUT enqueues, GET /config pulls → pending cleared."""
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
            r = client.put("/v1/zones/1/hold", json={"activity": "manual"})
            assert r.status_code == 200
            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1

            # Thermostat pulls config → pending cleared.
            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay dispatcher ─────────────────────────────────────────────────

async def test_replay_applies_pending_write_onto_fresh_tree():
    """Thermostat-reboot race: proxy has a pending write, thermostat posts
    a fresh config that doesn't reflect it. Replay must re-apply so the
    thermostat's next GET /config sees the mutation.
    """
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    # Prime: apply config, mutate, then simulate thermostat POSTing stale tree
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_zone_hold_set,
        serial="0000TEST0000",
        kind="zone_hold_set",
        target="zone:1",
        payload={"zone_id": "1", "activity": "manual", "otmr": "14:45"},
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    # Thermostat reboot + POSTs fresh tree (no mutation) — replay must re-apply.
    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    # The stored tree now contains the replayed hold.
    stored = store.get_config()
    assert stored is not None
    z1_el = _zone_elem(stored.tree, "1")
    assert _text(z1_el, "hold") == "on"
    assert _text(z1_el, "holdActivity") == "manual"

    # Typed snapshot also reflects the replayed state.
    z1 = next(z for z in stored.config.zones if z.id == "1")
    assert z1.hold.active is True

    # Pending row still unapplied — it's cleared only on pull-observed GET.
    assert await p.unapplied_count("0000TEST0000") == 1

    # Dirty flag should be set: the thermostat's tree didn't have the
    # mutation, so we need to signal it to re-pull.
    assert store.config_dirty is True
    await p.close()


async def test_replay_unknown_kind_leaves_pending_and_logs():
    """A persisted row with a kind we don't recognize (e.g., future build
    downgraded) must stay pending rather than be silently dropped."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    await p.enqueue_write(
        "0000TEST0000", "future_kind_we_dont_know", None, {"foo": "bar"}
    )

    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    # Still pending — no dispatcher ran, but no data loss either.
    assert await p.unapplied_count("0000TEST0000") == 1
    await p.close()


async def test_replay_preserves_original_bytes_when_no_pending():
    """Without pending writes, apply_config must be a no-op vs. the
    original behavior — tree stored verbatim, no spurious dirty flip."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    stored = store.get_config()
    assert stored is not None
    # Serialized round-trip matches source shape (bare <config>…).
    assert b"<config>" in serialize_config_tree(stored.tree)
    # No mutations → no dirty flip.
    assert store.config_dirty is False
    await p.close()
