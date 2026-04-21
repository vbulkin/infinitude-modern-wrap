"""Slice 10 — PUT /v1/zones/{id}/schedule.

Full 7-day program overwrite. PUT (not PATCH) because the body is the
whole program, not sparse fields; duplicate/missing day names are 422
so a client bug cannot silently drop a day.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_schedule_set
from infinitude_proxy.parser import parse_system_config_with_tree
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"

DAYS_OF_WEEK = [
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
]


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _make_period(pid: int, activity: str, time: str, enabled: bool = True) -> dict:
    return {"id": pid, "activity": activity, "time": time, "enabled": enabled}


def _make_week(periods_per_day: list[list[dict]] | None = None) -> list[dict]:
    """Build a seven-day list. Each day defaults to a simple wake+sleep
    pair so we have min-required (1) period coverage without encoding
    every day by hand in every test."""
    default = [
        _make_period(1, "wake", "06:00"),
        _make_period(2, "sleep", "22:00"),
    ]
    pp = periods_per_day or [default] * 7
    return [{"day": d, "periods": pp[i]} for i, d in enumerate(DAYS_OF_WEEK)]


def _day_el(tree: etree._Element, zone_id: str, day_name: str) -> etree._Element:
    zone = next(
        z for z in tree.find("zones").findall("zone") if z.get("id") == zone_id
    )
    prog = zone.find("program")
    return next(d for d in prog.findall("day") if d.get("id") == day_name)


# ── Mutation unit ─────────────────────────────────────────────────────

def test_apply_schedule_set_overwrites_program():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    apply_schedule_set(tree, {"zone_id": "1", "days": _make_week()})
    sunday = _day_el(tree, "1", "Sunday")
    periods = sunday.findall("period")
    assert len(periods) == 2
    p1 = periods[0]
    assert p1.get("id") == "1"
    assert p1.find("activity").text == "wake"
    assert p1.find("time").text == "06:00"
    assert p1.find("enabled").text == "on"


def test_apply_schedule_set_enabled_false_serializes_off():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    week = _make_week([
        [_make_period(1, "wake", "06:00", enabled=False),
         _make_period(2, "sleep", "22:00", enabled=True)]
    ] * 7)
    apply_schedule_set(tree, {"zone_id": "1", "days": week})
    monday = _day_el(tree, "1", "Monday")
    p1 = monday.find("period")
    assert p1.find("enabled").text == "off"


def test_apply_schedule_set_removes_prior_days():
    """Rebuild: any days present in the original program but absent in
    the payload would be dropped. We pass all 7 days here, but the point
    is that apply_schedule_set clears first rather than merging."""
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    zone = next(
        z for z in tree.find("zones").findall("zone") if z.get("id") == "1"
    )
    prog_before = zone.find("program")
    days_before = len(prog_before.findall("day"))
    assert days_before == 7
    apply_schedule_set(tree, {"zone_id": "1", "days": _make_week()})
    prog_after = zone.find("program")
    assert len(prog_after.findall("day")) == 7


def test_apply_schedule_set_unknown_zone_raises():
    tree, _ = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    try:
        apply_schedule_set(tree, {"zone_id": "99", "days": _make_week()})
    except ValueError as e:
        assert "99" in str(e)
    else:
        raise AssertionError("expected ValueError for unknown zone")


# ── StateStore ────────────────────────────────────────────────────────

async def test_mutate_config_schedule_persists_and_enqueues():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")
    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)

    updated = await store.mutate_config(
        apply_schedule_set,
        serial="0000TEST0000",
        kind="schedule_set",
        target="zone:1:schedule",
        payload={"zone_id": "1", "days": _make_week()},
    )
    assert updated is not None
    zone = updated.config.zones[0]
    assert len(zone.schedule) == 7
    sunday = next(d for d in zone.schedule if d.day == "Sunday")
    assert len(sunday.periods) == 2

    pending = await p.pending("0000TEST0000")
    assert len(pending) == 1
    assert pending[0].kind == "schedule_set"
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


def test_put_schedule_overwrites_and_echoes():
    client = _seed_client()
    resp = client.put("/v1/zones/1/schedule", json={"days": _make_week()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["zoneId"] == "1"
    assert len(body["days"]) == 7
    assert {d["day"] for d in body["days"]} == set(DAYS_OF_WEEK)


def test_put_schedule_rejects_missing_day():
    client = _seed_client()
    # Repeat Monday to make a 7-item list with Tuesday missing.
    bad = _make_week()
    bad[2] = {"day": "Monday", "periods": [_make_period(1, "wake", "06:00")]}
    resp = client.put("/v1/zones/1/schedule", json={"days": bad})
    assert resp.status_code == 422


def test_put_schedule_rejects_wrong_day_count():
    client = _seed_client()
    resp = client.put(
        "/v1/zones/1/schedule",
        json={"days": _make_week()[:6]},
    )
    assert resp.status_code == 422


def test_put_schedule_rejects_duplicate_period_ids():
    client = _seed_client()
    bad = _make_week()
    bad[0]["periods"] = [
        _make_period(1, "wake", "06:00"),
        _make_period(1, "sleep", "22:00"),
    ]
    resp = client.put("/v1/zones/1/schedule", json={"days": bad})
    assert resp.status_code == 422


def test_put_schedule_rejects_invalid_time_format():
    client = _seed_client()
    bad = _make_week()
    bad[0]["periods"] = [_make_period(1, "wake", "6:0")]
    resp = client.put("/v1/zones/1/schedule", json={"days": bad})
    assert resp.status_code == 422


def test_put_schedule_rejects_invalid_activity():
    client = _seed_client()
    bad = _make_week()
    bad[0]["periods"] = [_make_period(1, "eco", "06:00")]
    resp = client.put("/v1/zones/1/schedule", json={"days": bad})
    assert resp.status_code == 422


def test_put_schedule_rejects_extra_fields():
    client = _seed_client()
    resp = client.put(
        "/v1/zones/1/schedule",
        json={"days": _make_week(), "zoneId": "1"},
    )
    assert resp.status_code == 422


def test_put_schedule_rejects_empty_body():
    client = _seed_client()
    resp = client.put("/v1/zones/1/schedule", json={})
    assert resp.status_code == 422


def test_put_schedule_unknown_zone_404():
    client = _seed_client()
    resp = client.put("/v1/zones/99/schedule", json={"days": _make_week()})
    assert resp.status_code == 404


def test_put_schedule_before_config_404():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    resp = client.put("/v1/zones/1/schedule", json={"days": _make_week()})
    assert resp.status_code == 404


async def test_put_schedule_with_persistence_enqueues_pending():
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
            r = client.put(
                "/v1/zones/1/schedule", json={"days": _make_week()}
            )
            assert r.status_code == 200
            pending = await p.pending("0000TEST0000")
            assert len(pending) == 1
            assert pending[0].kind == "schedule_set"

            client.get("/systems/0000TEST0000/config")
            assert await p.unapplied_count("0000TEST0000") == 0
    finally:
        await p.close()


# ── Replay ────────────────────────────────────────────────────────────

async def test_replay_applies_schedule_onto_fresh_tree():
    p = await Persistence.open(":memory:")
    store = StateStore(persistence=p)
    xml = _read("boot_01_system_config.xml")

    tree, config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", config, tree)
    await store.mutate_config(
        apply_schedule_set,
        serial="0000TEST0000",
        kind="schedule_set",
        target="zone:1:schedule",
        payload={"zone_id": "1", "days": _make_week()},
    )
    assert await p.unapplied_count("0000TEST0000") == 1

    fresh_tree, fresh_config = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", fresh_config, fresh_tree)

    stored = store.get_config()
    assert stored is not None
    sunday = _day_el(stored.tree, "1", "Sunday")
    periods = sunday.findall("period")
    # Replayed 2-period week, not the fixture's 5-period default.
    assert len(periods) == 2
    assert periods[0].find("activity").text == "wake"
    assert store.config_dirty is True
    await p.close()
