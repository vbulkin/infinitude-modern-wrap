"""Slice 11 — SSE event-shape fix.

Covers the publisher unit (monotonic ids, ring-buffer replay semantics),
the state_store → publisher wiring (apply_telemetry / apply_config /
mutate_config all emit `state.update`; hold mutations also emit
`hold.changed`), and the /v1/events endpoint behavior around
Last-Event-ID replay / re-seed on gap. Live-wire SSE flow is covered
separately in test_sse_live.py.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.events import EVENT_BUFFER_SIZE, Event, EventPublisher
from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_zone_hold_clear, apply_zone_hold_set
from infinitude_proxy.parser import parse_system_config_with_tree, parse_telemetry
from infinitude_proxy.state_store import StateStore, _target_to_resource

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ── Publisher unit ────────────────────────────────────────────────────

async def test_publisher_assigns_monotonic_ids():
    p = EventPublisher()
    e1 = await p.publish("state.update", {"resource": "system", "changes": {}})
    e2 = await p.publish("state.update", {"resource": "system", "changes": {}})
    assert e1.id == 1
    assert e2.id == 2
    assert p.latest_id == 2


async def test_replay_since_returns_events_after_last_id():
    p = EventPublisher()
    for _ in range(5):
        await p.publish("state.update", {"resource": "system", "changes": {}})
    replay = p.replay_since(3)
    assert replay is not None
    assert [e.id for e in replay] == [4, 5]


async def test_replay_since_returns_empty_when_caught_up():
    p = EventPublisher()
    await p.publish("state.update", {"resource": "system", "changes": {}})
    replay = p.replay_since(1)
    assert replay == []


async def test_replay_since_returns_none_when_gap_too_wide():
    """Buffer size 3, publish 5 events, ask for id=1 — it's fallen off
    the end, so publisher returns None to signal re-seed required."""
    p = EventPublisher(buffer_size=3)
    for _ in range(5):
        await p.publish("state.update", {"resource": "system", "changes": {}})
    assert p.replay_since(1) is None


async def test_replay_since_empty_buffer_returns_empty_for_zero():
    p = EventPublisher()
    # A fresh client hasn't seen any event yet, and neither has the
    # publisher — they're trivially in sync.
    assert p.replay_since(0) == []


async def test_replay_since_empty_buffer_returns_none_for_nonzero():
    """Client claims a last_id higher than anything we've issued — that
    can only happen on a stale reconnect against a restarted publisher,
    so treat it as a gap and force a re-seed."""
    p = EventPublisher()
    assert p.replay_since(5) is None


async def test_subscribe_receives_subsequent_events():
    p = EventPublisher()
    q = p.subscribe()
    ev = await p.publish("state.update", {"resource": "system", "changes": {}})
    delivered = q.get_nowait()
    assert delivered is ev
    p.unsubscribe(q)
    assert p.subscriber_count == 0


async def test_buffer_caps_at_configured_size():
    p = EventPublisher(buffer_size=3)
    for _ in range(10):
        await p.publish("state.update", {"resource": "system", "changes": {}})
    # Latest 3 retained; ids 8/9/10 only.
    replay = p.replay_since(7)
    assert replay is not None
    assert [e.id for e in replay] == [8, 9, 10]


def test_default_buffer_size_is_200():
    # Protects the ring-buffer window from being reduced without
    # thinking about the reconnect-backfill assumption.
    assert EVENT_BUFFER_SIZE == 200


# ── target → resource translator ─────────────────────────────────────

def test_target_to_resource_system():
    assert _target_to_resource("system") == "system"


def test_target_to_resource_zone():
    assert _target_to_resource("zone:1") == "zones/1"


def test_target_to_resource_zone_schedule():
    assert _target_to_resource("zone:1:schedule") == "zones/1/schedule"


def test_target_to_resource_zone_activity():
    assert _target_to_resource("zone:1:activity:home") == "zones/1/activities/home"


def test_target_to_resource_vacation():
    assert _target_to_resource("vacation") == "system/vacation"


def test_target_to_resource_humidity():
    assert _target_to_resource("humidity") == "system/humidity"


def test_target_to_resource_none_defaults_to_system():
    assert _target_to_resource(None) == "system"


# ── StateStore publishes spec events ─────────────────────────────────

async def test_apply_telemetry_publishes_state_update():
    store = StateStore()
    snap = parse_telemetry(_read("telemetry_steady.xml"))
    await store.apply_telemetry("0000TEST0000", snap)
    assert store.events.latest_id == 1


async def test_apply_config_publishes_state_update():
    store = StateStore()
    tree, config = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    await store.apply_config("0000TEST0000", config, tree)
    assert store.events.latest_id == 1


async def test_mutate_config_publishes_state_update_with_resource():
    store = StateStore()
    tree, config = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    await store.apply_config("0000TEST0000", config, tree)
    q = store.events.subscribe()
    # drain apply_config event first (queued before subscribe? no — subscribe
    # happens after, so only subsequent events land here).
    await store.mutate_config(
        apply_zone_hold_set,
        serial="0000TEST0000",
        kind="zone_hold_set",
        target="zone:1",
        payload={"zone_id": "1", "activity": "home", "otmr": ""},
    )
    # Two events: state.update + hold.changed
    ev1 = q.get_nowait()
    ev2 = q.get_nowait()
    assert ev1.event == "state.update"
    assert ev1.data["resource"] == "zones/1"
    assert "zone_id" not in ev1.data["changes"]
    assert ev1.data["changes"]["activity"] == "home"
    assert ev2.event == "hold.changed"
    assert ev2.data["resource"] == "zones/1/hold"
    assert ev2.data["state"] == "active"
    assert ev2.data["activity"] == "home"


async def test_mutate_config_hold_clear_publishes_hold_changed_cleared():
    store = StateStore()
    tree, config = parse_system_config_with_tree(_read("boot_01_system_config.xml"))
    await store.apply_config("0000TEST0000", config, tree)
    q = store.events.subscribe()
    await store.mutate_config(
        apply_zone_hold_clear,
        serial="0000TEST0000",
        kind="zone_hold_clear",
        target="zone:1",
        payload={"zone_id": "1"},
    )
    ev1 = q.get_nowait()
    ev2 = q.get_nowait()
    assert ev1.event == "state.update"
    assert ev2.event == "hold.changed"
    assert ev2.data["state"] == "cleared"


# ── /v1/events HTTP behavior ─────────────────────────────────────────

def _seeded_client() -> tuple[TestClient, StateStore]:
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    return client, store


def test_notifications_publish_notifications_received_event():
    """alpha.31: thermostat notifications fire a `notifications.received`
    SSE event so HA-side consumers see them in real time instead of
    waiting for the next REST poll. Payload carries serial + count +
    parsed event list."""
    client, store = _seeded_client()
    before = store.events.latest_id
    r = client.post(
        "/systems/0000TEST0000/notifications",
        content=_read("change_opmode_notifications.xml"),
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    # Event publisher's id counter advanced.
    assert store.events.latest_id > before
    # New events in the buffer include a notifications.received.
    recent = store.events.replay_since(before) or []
    types = [e.event for e in recent]
    assert "notifications.received" in types
    nr = next(e for e in recent if e.event == "notifications.received")
    assert nr.data["serial"] == "0000TEST0000"
    assert nr.data["count"] >= 1
    assert isinstance(nr.data["events"], list)
    assert len(nr.data["events"]) == nr.data["count"]


def test_empty_notifications_post_skips_sse_publish():
    """An empty notifications POST shouldn't bump the publisher's id —
    no consumer needs to know that nothing happened."""
    client, store = _seeded_client()
    before = store.events.latest_id
    # Synthesise an empty <notifications/> body.
    r = client.post(
        "/systems/0000TEST0000/notifications",
        content=b'<?xml version="1.0"?><notifications/>',
        headers={"content-type": "application/xml"},
    )
    assert r.status_code == 200
    assert store.events.latest_id == before


def test_zone_hold_put_publishes_hold_changed():
    client, store = _seeded_client()
    r = client.put(
        "/v1/zones/1/hold",
        json={"activity": "home"},
    )
    assert r.status_code == 200
    # apply_config published 1 event; hold PUT publishes state.update + hold.changed.
    recent = store.events.replay_since(0)
    assert recent is not None
    types = [e.event for e in recent]
    assert "hold.changed" in types
    hc = next(e for e in recent if e.event == "hold.changed")
    assert hc.data["resource"] == "zones/1/hold"
    assert hc.data["state"] == "active"


def test_system_hold_delete_publishes_hold_changed_cleared():
    client, store = _seeded_client()
    # First engage the hold so DELETE has something to release.
    client.put("/v1/system/hold", json={"activity": "home"})
    r = client.delete("/v1/system/hold")
    assert r.status_code == 200
    recent = store.events.replay_since(0)
    assert recent is not None
    cleared = [
        e for e in recent
        if e.event == "hold.changed" and e.data.get("state") == "cleared"
    ]
    assert len(cleared) == 1
    assert cleared[0].data["resource"] == "system/hold"
