"""Tests for the exercise_mutations.py walk-through script.

The script issues real HTTP, so the test scope is the plan-shaping
logic (which mode to flip to, plan length, step names). Actually
running the plan is covered live against a real addon during a
fixture harvest or post-cutover smoke run.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import exercise_mutations as em  # noqa: E402


def test_pick_alt_mode_prefers_fanonly():
    """Picking a non-current mode for the flip should default to the
    least-disruptive HVAC state (fan-only), so the walk doesn't swing
    heat/cool during a fixture capture."""
    assert em._pick_alt_mode("cool") == "fanonly"
    assert em._pick_alt_mode("heat") == "fanonly"
    assert em._pick_alt_mode("auto") == "fanonly"
    assert em._pick_alt_mode("off") == "fanonly"


def test_pick_alt_mode_falls_through_when_current_is_fanonly():
    """When already in fanonly, next-best is auto — still no heat/cool
    command issued."""
    assert em._pick_alt_mode("fanonly") == "auto"


@pytest.fixture
def fake_state():
    return {
        "_base_url": "http://test",
        "system": {"mode": "cool"},
        "zones": [
            {"id": "1", "heatSetpoint": 68, "coolSetpoint": 76},
            {"id": "2", "heatSetpoint": 70, "coolSetpoint": 74},
        ],
    }


def test_build_plan_covers_every_mutation_kind(fake_state):
    """The walk must include every mutation kind in mutations.REPLAY_REGISTRY
    at least once — this is what makes the output a full fixture anchor set.
    Names suffixed ':rev' / ':on' / ':off' are counted as the same kind."""
    with patch.object(em, "_request") as mock_req:
        mock_req.side_effect = [
            {"targetHome": 45, "targetAway": 40, "targetVacation": 35},
            [{"id": "home", "heat": 68, "cool": 76}, {"id": "away", "heat": 62, "cool": 80}],
        ]
        plan = em._build_plan(fake_state, "1", include_schedule=False)

    base_kinds = {name.split(":", 1)[0] for name, _ in plan}
    assert base_kinds == {
        "zone_setpoints_set",
        "zone_hold_set",
        "zone_hold_clear",
        "system_hold_set",
        "system_hold_clear",
        "system_mode_set",
        "vacation_set",
        "humidity_set",
        "activity_set",
    }


def test_build_plan_schedule_opt_in(fake_state):
    """schedule_set is off by default — walk should exclude it unless
    --include-schedule is passed."""
    with patch.object(em, "_request") as mock_req:
        mock_req.side_effect = [
            {"targetHome": 45},
            [{"id": "home", "heat": 68, "cool": 76}],
        ]
        plan_default = em._build_plan(fake_state, "1", include_schedule=False)
    names_default = {n.split(":", 1)[0] for n, _ in plan_default}
    assert "schedule_set" not in names_default

    with patch.object(em, "_request") as mock_req:
        mock_req.side_effect = [
            {"targetHome": 45},
            [{"id": "home", "heat": 68, "cool": 76}],
        ]
        plan_sched = em._build_plan(fake_state, "1", include_schedule=True)
    names_sched = {n.split(":", 1)[0] for n, _ in plan_sched}
    assert "schedule_set" in names_sched


def test_build_plan_unknown_zone_fails_loudly(fake_state):
    """Targeting a zone that's not in /v1/state should raise with the
    available ids — silent "plan produced no zone actions" would be a
    confusing failure mode during a fixture run."""
    with patch.object(em, "_request") as mock_req:
        mock_req.side_effect = [{"targetHome": 45}, []]
        with pytest.raises(SystemExit, match="zone 9 not found"):
            em._build_plan(fake_state, "9", include_schedule=False)


def test_build_plan_paired_reverses_for_each_mutation(fake_state):
    """Every bump should be followed by a restore so the thermostat
    ends the walk near its starting state — critical when the walk
    is run against live hardware."""
    with patch.object(em, "_request") as mock_req:
        mock_req.side_effect = [
            {"targetHome": 45},
            [{"id": "home", "heat": 68, "cool": 76}],
        ]
        plan = em._build_plan(fake_state, "1", include_schedule=False)
    names = [n for n, _ in plan]
    # Set/reverse pairs (order within the walk is intentional — holds
    # are exercised before mode flips so we don't trap the thermostat
    # in a hold-on-off-mode state between steps).
    assert "zone_setpoints_set" in names and "zone_setpoints_set:rev" in names
    assert "system_mode_set" in names and "system_mode_set:rev" in names
    assert "vacation_set:on" in names and "vacation_set:off" in names
    assert "humidity_set" in names and "humidity_set:rev" in names
    assert "activity_set" in names and "activity_set:rev" in names
