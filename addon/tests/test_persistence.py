"""Persistence layer — aiosqlite schema, state cache, pending writes.

Tests cover three axes:
  - round-trip: save → load returns exact bytes + dirty flag + idu/odu
  - pending writes: enqueue → pending → mark_applied / mark_all_applied
  - StateStore integration: apply_config persists, restore rehydrates,
    /v1/healthz picks up pendingPushes

SQLite uses `:memory:` so tests are hermetic and fast; file-backed DB
semantics (WAL, crash recovery) aren't exercised here — they're the
same SQLite primitives we're already trusting.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import parse_system_config_with_tree
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ── state_cache round-trip ──────────────────────────────────────────

async def test_save_and_load_config_round_trips_bytes():
    p = await Persistence.open(":memory:")
    xml = _read("boot_01_system_config.xml")
    await p.save_config("0000TEST0000", xml)
    snap = await p.load("0000TEST0000")
    assert snap is not None
    assert snap.config_xml == xml
    assert snap.idu_xml is None
    assert snap.odu_xml is None
    assert snap.config_dirty is False
    await p.close()


async def test_partial_upsert_preserves_other_columns():
    """save_idu after save_config must NOT nullify config_xml."""
    p = await Persistence.open(":memory:")
    await p.save_config("S1", b"<config/>")
    await p.save_idu("S1", b"<idu_config/>")
    await p.save_odu("S1", b"<odu_config/>")
    snap = await p.load("S1")
    assert snap is not None
    assert snap.config_xml == b"<config/>"
    assert snap.idu_xml == b"<idu_config/>"
    assert snap.odu_xml == b"<odu_config/>"
    await p.close()


async def test_save_config_dirty_round_trips():
    p = await Persistence.open(":memory:")
    await p.save_config("S1", b"<config/>")
    await p.save_config_dirty("S1", True)
    snap = await p.load("S1")
    assert snap is not None and snap.config_dirty is True
    await p.save_config_dirty("S1", False)
    snap = await p.load("S1")
    assert snap is not None and snap.config_dirty is False
    await p.close()


async def test_load_any_returns_most_recent():
    import asyncio
    p = await Persistence.open(":memory:")
    await p.save_config("OLD", b"<config>old</config>")
    # time.time() resolution on Windows can collide; tiny gap guarantees order
    await asyncio.sleep(0.01)
    await p.save_config("NEW", b"<config>new</config>")
    snap = await p.load_any()
    assert snap is not None
    assert snap.serial == "NEW"
    await p.close()


async def test_load_missing_serial_returns_none():
    p = await Persistence.open(":memory:")
    assert await p.load("NOPE") is None
    assert await p.load_any() is None
    await p.close()


# ── pending_writes ──────────────────────────────────────────────────

async def test_enqueue_and_list_pending_oldest_first():
    p = await Persistence.open(":memory:")
    id1 = await p.enqueue_write("S1", "zone_hold", "1", {"otmr": "18:00"})
    id2 = await p.enqueue_write("S1", "zone_hold", "2", {"otmr": "19:00"})
    rows = await p.pending("S1")
    assert [r.id for r in rows] == [id1, id2]
    assert rows[0].kind == "zone_hold"
    assert rows[0].target == "1"
    assert rows[0].payload == {"otmr": "18:00"}
    await p.close()


async def test_mark_applied_makes_row_invisible_to_pending():
    p = await Persistence.open(":memory:")
    id1 = await p.enqueue_write("S1", "zone_hold", "1", {})
    id2 = await p.enqueue_write("S1", "zone_hold", "2", {})
    await p.mark_applied([id1])
    rows = await p.pending("S1")
    assert [r.id for r in rows] == [id2]
    await p.close()


async def test_mark_all_applied_clears_serial_queue():
    p = await Persistence.open(":memory:")
    await p.enqueue_write("S1", "zone_hold", "1", {})
    await p.enqueue_write("S1", "zone_hold", "2", {})
    await p.enqueue_write("S2", "zone_hold", "1", {})
    affected = await p.mark_all_applied("S1")
    assert len(affected) == 2
    assert await p.pending("S1") == []
    # S2 untouched
    assert len(await p.pending("S2")) == 1
    await p.close()


async def test_mark_applied_is_idempotent():
    """Double-apply must not overwrite the original applied_at."""
    p = await Persistence.open(":memory:")
    id1 = await p.enqueue_write("S1", "zone_hold", "1", {})
    await p.mark_applied([id1])
    # Second call is a no-op
    await p.mark_applied([id1])
    assert await p.pending("S1") == []
    await p.close()


async def test_unapplied_count_and_oldest_age():
    p = await Persistence.open(":memory:")
    assert await p.unapplied_count() == 0
    assert await p.oldest_pending_age_seconds() is None
    await p.enqueue_write("S1", "zone_hold", "1", {})
    await p.enqueue_write("S1", "zone_hold", "2", {})
    assert await p.unapplied_count() == 2
    age = await p.oldest_pending_age_seconds()
    assert age is not None and age >= 0.0
    await p.close()


# ── migrations ──────────────────────────────────────────────────────

async def test_reopen_is_idempotent():
    """Re-opening an existing DB must not re-run migrations destructively."""
    p = await Persistence.open(":memory:")
    await p.save_config("S1", b"<config/>")
    await p.close()
    # :memory: connections don't persist across close, so this is a fresh DB —
    # we verify the migrate path runs cleanly when schema_version row exists
    # by forcing it via a file DB (tmp) below.


async def test_reopen_file_db_preserves_data(tmp_path: Path):
    db = tmp_path / "state.db"
    p = await Persistence.open(db)
    await p.save_config("S1", b"<config/>")
    await p.enqueue_write("S1", "zone_hold", "1", {"x": 1})
    await p.close()
    # Reopen — migration's schema_version sentinel exists; must be a no-op
    p2 = await Persistence.open(db)
    snap = await p2.load("S1")
    assert snap is not None and snap.config_xml == b"<config/>"
    rows = await p2.pending("S1")
    assert len(rows) == 1 and rows[0].payload == {"x": 1}
    await p2.close()


# ── StateStore integration ──────────────────────────────────────────

async def test_state_store_apply_config_persists_serialized_tree():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    snap = await p.load("0000TEST0000")
    assert snap is not None
    # Stored bytes are the serialized tree (XML declaration + <config>),
    # NOT the raw POST body — the tree is what we'd serve on GET /config.
    assert snap.config_xml is not None
    assert snap.config_xml.startswith(b'<?xml')
    assert b"<config" in snap.config_xml
    await p.close()


async def test_state_store_mark_dirty_persists_flag():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mark_config_dirty()
    snap = await p.load("0000TEST0000")
    assert snap is not None and snap.config_dirty is True
    # take_config_dirty clears both memory AND disk
    was_dirty = await store.take_config_dirty()
    assert was_dirty is True
    snap = await p.load("0000TEST0000")
    assert snap is not None and snap.config_dirty is False
    await p.close()


async def test_restore_from_persistence_rehydrates_config_and_dirty():
    """New StateStore pointed at a non-empty DB must see the prior state."""
    p = await Persistence.open(":memory:")
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    # Store via one StateStore, then spin up a fresh one and restore
    store1 = StateStore(persistence=p)
    await store1.apply_config("0000TEST0000", config, tree)
    await store1.mark_config_dirty()

    store2 = StateStore(persistence=p)
    assert store2.get_config() is None  # nothing in memory yet
    await store2.restore_from_persistence()
    restored = store2.get_config()
    assert restored is not None
    assert restored.serial == "0000TEST0000"
    assert store2.config_dirty is True
    await p.close()


async def test_restore_skips_corrupt_config_blob(caplog):
    p = await Persistence.open(":memory:")
    await p.save_config("0000TEST0000", b"<not-valid-xml")
    store = StateStore(persistence=p)
    # Must not raise — corrupt blob logs and falls through
    await store.restore_from_persistence()
    assert store.get_config() is None
    await p.close()


async def test_idu_odu_persistence_and_restore():
    p = await Persistence.open(":memory:")
    idu_xml = _read("boot_03_idu_config.xml")
    odu_xml = _read("boot_04_odu_config.xml")
    from infinitude_proxy.parser import parse_idu_config, parse_odu_config
    store = StateStore(persistence=p)
    await store.apply_idu("S1", parse_idu_config(idu_xml), raw_xml=idu_xml)
    await store.apply_odu("S1", parse_odu_config(odu_xml), raw_xml=odu_xml)

    store2 = StateStore(persistence=p)
    await store2.restore_from_persistence()
    assert store2.get_idu() is not None
    assert store2.get_odu() is not None
    await p.close()


# ── /v1/healthz integration ─────────────────────────────────────────

async def test_healthz_pending_pushes_counts_from_persistence():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    await p.enqueue_write("S1", "zone_hold", "1", {})
    await p.enqueue_write("S1", "zone_hold", "2", {})

    app = create_app(store=store)
    with TestClient(app) as client:
        resp = client.get("/v1/healthz")
    assert resp.status_code == 200
    body = resp.json()
    ss = body["components"]["stateStore"]
    assert ss["pendingPushes"] == 2
    assert ss["oldestPendingPushAgeSeconds"] is not None
    assert ss["oldestPendingPushAgeSeconds"] >= 0
    await p.close()


# ── pull-observed clear ─────────────────────────────────────────────

async def test_get_config_pull_marks_pending_applied():
    """GET /systems/{serial}/config clears pending writes for that serial."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await p.enqueue_write("0000TEST0000", "zone_hold", "1", {})
    await p.enqueue_write("0000TEST0000", "zone_hold", "2", {})
    assert await p.unapplied_count() == 2

    app = create_app(store=store)
    with TestClient(app) as client:
        resp = client.get("/systems/0000TEST0000/config")
    assert resp.status_code == 200
    assert await p.unapplied_count() == 0
    await p.close()


async def test_apply_config_with_pending_writes_preserves_pending_row():
    """Until Slice 2 replay lands, pending rows must survive a thermostat
    config POST — dropping them would silently lose writes."""
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    await p.enqueue_write("0000TEST0000", "zone_hold", "1", {})
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    assert await p.unapplied_count() == 1
    await p.close()


# ── mid-session failure tolerance ───────────────────────────────────

async def test_apply_config_survives_persistence_write_failure():
    """A mid-session SQLite failure must NOT propagate out — otherwise
    the southbound handler returns 500 to the thermostat, which then
    retries and may never stabilize. In-memory state wins; disk catches
    up on the next successful write."""
    class BrokenPersistence:
        async def save_config(self, serial, xml):
            raise RuntimeError("disk full (simulated)")
        async def save_config_dirty(self, serial, dirty):
            raise RuntimeError("disk full (simulated)")
        async def pending(self, serial=None):
            return []

    store = StateStore(persistence=BrokenPersistence())  # type: ignore[arg-type]
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    # Must not raise
    await store.apply_config("0000TEST0000", config, tree)
    # Memory got the update even though disk didn't
    stored = store.get_config()
    assert stored is not None and stored.serial == "0000TEST0000"
    # mark_config_dirty is likewise resilient
    await store.mark_config_dirty()
    assert store.config_dirty is True
