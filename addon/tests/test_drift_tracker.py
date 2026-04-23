"""Unit + integration tests for mutation drift detection.

Unit section covers DriftTracker and intents_for_mutation in isolation.
Integration section exercises the StateStore wiring (mutate_config arms
intents, apply_telemetry observes, healthz exposes counters) against the
FastAPI app.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from infinitude_proxy.drift import (
    EVENT_HISTORY,
    DriftIntent,
    DriftTracker,
    _make_intent,
    intents_for_mutation,
)
from infinitude_proxy.main import create_app
from infinitude_proxy.mutations import apply_zone_setpoints_set
from infinitude_proxy.parser import (
    TelemetrySnapshot,
    parse_system_config_with_tree,
    parse_telemetry,
)
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _baseline() -> TelemetrySnapshot:
    """Fresh snapshot from the steady-state fixture.

    The fixture has two enabled zones ("1" and "2"). We mutate copies
    of the parsed model in individual tests to simulate telemetry
    drift / acceptance.
    """
    return parse_telemetry((FIXTURES / "telemetry_steady.xml").read_bytes())


def _snapshot_with(
    *,
    zone_id: str,
    cool: int | None = None,
    heat: int | None = None,
    hold_active: bool | None = None,
) -> TelemetrySnapshot:
    snap = _baseline()
    updated_zones = []
    for z in snap.zones:
        if z.id == zone_id:
            patch: dict = {}
            if cool is not None:
                patch["coolSetpoint"] = cool
            if heat is not None:
                patch["heatSetpoint"] = heat
            if hold_active is not None:
                patch["holdActive"] = hold_active
            updated_zones.append(z.model_copy(update=patch))
        else:
            updated_zones.append(z)
    return snap.model_copy(update={"zones": updated_zones})


# ── DriftTracker unit tests ──────────────────────────────────────────


def test_observe_with_no_armed_intents_returns_empty():
    tracker = DriftTracker()
    events = tracker.observe(_baseline())
    assert events == []
    assert tracker.drift_count == 0
    assert tracker.armed_count == 0


def test_armed_intent_matches_disarms_without_firing():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker()
    tracker.arm([
        _make_intent("zone_setpoints_set", "zones/1", "coolSetpoint", 78, now=t0),
    ])
    snap = _snapshot_with(zone_id="1", cool=78)
    events = tracker.observe(snap, now=t0 + timedelta(seconds=30))
    assert events == []
    assert tracker.armed_count == 0
    assert tracker.drift_count == 0


def test_mismatch_within_grace_stays_armed():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker()
    tracker.arm([
        _make_intent("zone_setpoints_set", "zones/1", "coolSetpoint", 78, now=t0),
    ])
    snap = _snapshot_with(zone_id="1", cool=75)
    events = tracker.observe(snap, now=t0 + timedelta(seconds=30))
    assert events == []
    assert tracker.armed_count == 1
    assert tracker.drift_count == 0


def test_mismatch_past_grace_fires_and_disarms():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker()
    tracker.arm([
        _make_intent("zone_setpoints_set", "zones/1", "coolSetpoint", 78, now=t0),
    ])
    past_grace = t0 + timedelta(seconds=181)
    snap = _snapshot_with(zone_id="1", cool=75)
    events = tracker.observe(snap, now=past_grace)
    assert len(events) == 1
    ev = events[0]
    assert ev.kind == "zone_setpoints_set"
    assert ev.target == "zones/1"
    assert ev.field == "coolSetpoint"
    assert ev.expected == 78
    assert ev.observed == 75
    assert ev.detected_at == past_grace
    assert tracker.armed_count == 0
    assert tracker.drift_count == 1
    assert tracker.last_drift_at == past_grace


def test_single_intent_fires_only_once():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker()
    tracker.arm([
        _make_intent("zone_setpoints_set", "zones/1", "coolSetpoint", 78, now=t0),
    ])
    past_grace = t0 + timedelta(seconds=200)
    snap = _snapshot_with(zone_id="1", cool=75)
    tracker.observe(snap, now=past_grace)
    assert tracker.drift_count == 1
    events_second = tracker.observe(snap, now=past_grace + timedelta(seconds=90))
    assert events_second == []
    assert tracker.drift_count == 1


def test_missing_zone_stays_armed_then_times_out_without_firing():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker()
    tracker.arm([
        _make_intent(
            "zone_setpoints_set", "zones/99", "coolSetpoint", 78, now=t0
        ),
    ])
    snap = _baseline()
    # Within grace: intent still armed.
    events = tracker.observe(snap, now=t0 + timedelta(seconds=30))
    assert events == []
    assert tracker.armed_count == 1
    # Past grace: disarms silently (can't distinguish absent target from drift).
    events = tracker.observe(snap, now=t0 + timedelta(seconds=300))
    assert events == []
    assert tracker.armed_count == 0
    assert tracker.drift_count == 0


def test_mixed_armed_intents_fire_independently():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker()
    tracker.arm([
        _make_intent("zone_setpoints_set", "zones/1", "coolSetpoint", 78, now=t0),
        _make_intent("zone_setpoints_set", "zones/1", "heatSetpoint", 70, now=t0),
        _make_intent("zone_setpoints_set", "zones/1", "holdActive", True, now=t0),
    ])
    # Telemetry matches heat + hold, but cool drifted.
    snap = _snapshot_with(zone_id="1", cool=75, heat=70, hold_active=True)
    events = tracker.observe(snap, now=t0 + timedelta(seconds=200))
    assert len(events) == 1
    assert events[0].field == "coolSetpoint"
    # Other two matched and disarmed; drifted one fired and disarmed.
    assert tracker.armed_count == 0


def test_recent_events_bounded_to_history():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker()
    for i in range(EVENT_HISTORY + 5):
        tracker.arm([
            _make_intent(
                "zone_setpoints_set", "zones/1", "coolSetpoint",
                78 + i, now=t0,
            ),
        ])
        snap = _snapshot_with(zone_id="1", cool=60)
        tracker.observe(snap, now=t0 + timedelta(seconds=200))
    assert tracker.drift_count == EVENT_HISTORY + 5
    assert len(tracker.recent_events()) == EVENT_HISTORY


# ── intents_for_mutation unit tests ──────────────────────────────────


def test_intents_zone_setpoints_with_cool_and_hold():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    payload = {"zone_id": "1", "cool": 78, "heat": None, "activate_hold": True}
    intents = intents_for_mutation("zone_setpoints_set", payload, now=now)
    fields = {i.field for i in intents}
    assert fields == {"coolSetpoint", "holdActive"}
    cool_intent = next(i for i in intents if i.field == "coolSetpoint")
    assert cool_intent.expected == 78
    assert cool_intent.target == "zones/1"
    assert cool_intent.armed_at == now
    hold_intent = next(i for i in intents if i.field == "holdActive")
    assert hold_intent.expected is True


def test_intents_zone_setpoints_activate_hold_false_omits_hold():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    payload = {"zone_id": "1", "cool": 78, "heat": 68, "activate_hold": False}
    intents = intents_for_mutation("zone_setpoints_set", payload, now=now)
    fields = {i.field for i in intents}
    assert fields == {"coolSetpoint", "heatSetpoint"}


def test_intents_zone_setpoints_missing_activate_hold_defaults_to_engaged():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    payload = {"zone_id": "1", "cool": 78}
    intents = intents_for_mutation("zone_setpoints_set", payload, now=now)
    fields = {i.field for i in intents}
    assert fields == {"coolSetpoint", "holdActive"}


def test_intents_zone_hold_set_arms_hold_active_true():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    payload = {"zone_id": "2", "activity": "manual", "otmr": ""}
    intents = intents_for_mutation("zone_hold_set", payload, now=now)
    assert len(intents) == 1
    assert intents[0].target == "zones/2"
    assert intents[0].field == "holdActive"
    assert intents[0].expected is True


def test_intents_zone_hold_clear_arms_hold_active_false():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    intents = intents_for_mutation("zone_hold_clear", {"zone_id": "1"}, now=now)
    assert len(intents) == 1
    assert intents[0].field == "holdActive"
    assert intents[0].expected is False


def test_intents_uninstrumented_kinds_return_empty():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    # MVP skips these — backlog tracks extending coverage.
    for kind in (
        "schedule_set",
        "activity_set",
        "vacation_set",
        "humidity_set",
        "system_mode_set",
        "system_hold_set",
        "system_hold_clear",
    ):
        assert intents_for_mutation(kind, {}, now=now) == []


def test_intents_missing_zone_id_returns_empty():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    assert intents_for_mutation("zone_setpoints_set", {"cool": 78}, now=now) == []
    assert intents_for_mutation("zone_hold_set", {}, now=now) == []
    assert intents_for_mutation("zone_hold_clear", {}, now=now) == []


def test_intents_zone_setpoints_with_only_heat():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    payload = {"zone_id": "1", "cool": None, "heat": 70, "activate_hold": True}
    intents = intents_for_mutation("zone_setpoints_set", payload, now=now)
    fields = {i.field for i in intents}
    assert fields == {"heatSetpoint", "holdActive"}
    heat = next(i for i in intents if i.field == "heatSetpoint")
    assert heat.expected == 70


def test_drift_intent_ids_are_unique():
    now = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    payload = {"zone_id": "1", "cool": 78, "heat": 70}
    intents = intents_for_mutation("zone_setpoints_set", payload, now=now)
    ids = {i.intent_id for i in intents}
    assert len(ids) == len(intents)


def test_observe_with_grace_override():
    t0 = datetime(2026, 4, 23, 19, 0, tzinfo=timezone.utc)
    tracker = DriftTracker(grace=timedelta(seconds=30))
    tracker.arm([
        _make_intent("zone_setpoints_set", "zones/1", "coolSetpoint", 78, now=t0),
    ])
    snap = _snapshot_with(zone_id="1", cool=75)
    # At t0+31s, past the shorter grace.
    events = tracker.observe(snap, now=t0 + timedelta(seconds=31))
    assert len(events) == 1
    assert tracker.drift_count == 1


# ── StateStore integration tests ──────────────────────────────────────


def _seed_config(store: StateStore) -> None:
    """Prime the store with the fixture config so mutate_config can run."""
    import asyncio
    xml = (FIXTURES / "boot_01_system_config.xml").read_bytes()
    tree, cfg = parse_system_config_with_tree(xml)
    asyncio.get_event_loop().run_until_complete(
        store.apply_config("0000TEST0000", cfg, tree)
    )


async def test_mutate_config_arms_drift_intents():
    store = StateStore()
    xml = (FIXTURES / "boot_01_system_config.xml").read_bytes()
    tree, cfg = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", cfg, tree)

    assert store.drift.armed_count == 0
    await store.mutate_config(
        apply_zone_setpoints_set,
        serial="0000TEST0000",
        kind="zone_setpoints_set",
        target="zone:1",
        payload={"zone_id": "1", "cool": 78, "heat": None, "activate_hold": True},
    )
    # Intent fan-out: coolSetpoint + holdActive (heat omitted).
    assert store.drift.armed_count == 2


async def test_apply_telemetry_disarms_matching_intents():
    store = StateStore()
    xml = (FIXTURES / "boot_01_system_config.xml").read_bytes()
    tree, cfg = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", cfg, tree)
    await store.mutate_config(
        apply_zone_setpoints_set,
        serial="0000TEST0000",
        kind="zone_setpoints_set",
        target="zone:1",
        payload={"zone_id": "1", "cool": 78, "heat": None, "activate_hold": True},
    )
    assert store.drift.armed_count == 2

    # Build a telemetry snapshot matching the mutation.
    base = parse_telemetry((FIXTURES / "telemetry_steady.xml").read_bytes())
    matched_zones = [
        z.model_copy(update={"coolSetpoint": 78, "holdActive": True})
        if z.id == "1" else z
        for z in base.zones
    ]
    matched = base.model_copy(update={"zones": matched_zones})
    await store.apply_telemetry("0000TEST0000", matched)

    assert store.drift.armed_count == 0
    assert store.drift.drift_count == 0


async def test_apply_telemetry_fires_drift_past_grace():
    store = StateStore()
    # Shrink grace so the test doesn't have to wait 180 seconds.
    store.drift = DriftTracker(grace=timedelta(seconds=0))

    xml = (FIXTURES / "boot_01_system_config.xml").read_bytes()
    tree, cfg = parse_system_config_with_tree(xml)
    await store.apply_config("0000TEST0000", cfg, tree)
    await store.mutate_config(
        apply_zone_setpoints_set,
        serial="0000TEST0000",
        kind="zone_setpoints_set",
        target="zone:1",
        payload={"zone_id": "1", "cool": 78, "heat": None, "activate_hold": False},
    )
    # One intent for cool, none for hold (activate_hold=False).
    assert store.drift.armed_count == 1

    # Telemetry reports pre-mutation value → drift fires.
    base = parse_telemetry((FIXTURES / "telemetry_steady.xml").read_bytes())
    drifted_zones = [
        z.model_copy(update={"coolSetpoint": 75}) if z.id == "1" else z
        for z in base.zones
    ]
    drifted = base.model_copy(update={"zones": drifted_zones})
    await store.apply_telemetry("0000TEST0000", drifted)

    assert store.drift.armed_count == 0
    assert store.drift.drift_count == 1
    events = store.drift.recent_events()
    assert len(events) == 1
    assert events[0].field == "coolSetpoint"
    assert events[0].expected == 78
    assert events[0].observed == 75


def test_healthz_exposes_mutation_drift_with_zero_counters():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    resp = client.get("/v1/healthz")
    assert resp.status_code == 200
    drift_field = resp.json()["components"]["stateStore"]["mutationDrift"]
    assert drift_field["driftCount"] == 0
    assert drift_field["armedIntents"] == 0
    assert drift_field["lastDriftAt"] is None
    assert drift_field["graceSeconds"] == 180
    assert drift_field["recentEvents"] == []


def test_healthz_reflects_armed_intents_after_patch():
    store = StateStore()
    app = create_app(store=store)
    client = TestClient(app)

    client.post(
        "/systems/0000TEST0000",
        content=(FIXTURES / "boot_01_system_config.xml").read_bytes(),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch(
        "/v1/zones/1", json={"cool": 78, "activateHold": True}
    )
    assert resp.status_code == 200

    health = client.get("/v1/healthz").json()
    drift_field = health["components"]["stateStore"]["mutationDrift"]
    assert drift_field["driftCount"] == 0
    # coolSetpoint + holdActive.
    assert drift_field["armedIntents"] == 2
    assert drift_field["recentEvents"] == []
