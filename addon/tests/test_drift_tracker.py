"""Unit tests for DriftTracker and intents_for_mutation.

Tests the detector in isolation — no FastAPI app, no StateStore, no
persistence. Integration with mutate_config / apply_telemetry is covered
separately once drift wiring lands in state_store.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from infinitude_proxy.drift import (
    EVENT_HISTORY,
    DriftIntent,
    DriftTracker,
    _make_intent,
    intents_for_mutation,
)
from infinitude_proxy.parser import TelemetrySnapshot, parse_telemetry

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
