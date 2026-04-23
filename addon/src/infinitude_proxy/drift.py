"""Mutation drift detector.

Arms an intent per northbound mutation describing what the telemetry
should report once the thermostat has accepted the write. Telemetry
ticks evaluate armed intents:

  - expected == observed → intent disarms (mutation accepted)
  - mismatch AND armed_at older than the grace window → intent disarms
    and a DriftEvent is recorded (silent reject)
  - mismatch within the grace window → intent stays armed, retry next tick

Drift is the signal we were missing when the write-path silent-reject bug
shipped against the real thermostat: the pending-write row cleared on the
next GET /config (pull-observed clear) yet telemetry kept reporting the
pre-mutation values. Recording these as healthz counters turns that class
of regression into an observable rather than a user-reported surprise.

MVP instruments only the mutation kinds with an unambiguous telemetry
signal (zone setpoints, zone hold). Extending to schedule/vacation/
humidity/activity/system-mode/system-hold needs per-kind signal design —
see project_backlog.md.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .parser import TelemetrySnapshot

logger = logging.getLogger(__name__)

# Grace window: 2× the expected ~90s telemetry cadence. Shorter risks
# false positives on legitimate propagation lag; longer lets silent
# rejects linger unreported.
DEFAULT_GRACE = timedelta(seconds=180)

EVENT_HISTORY = 20


@dataclass(frozen=True)
class DriftIntent:
    intent_id: str
    kind: str
    target: str
    field: str
    expected: Any
    armed_at: datetime


@dataclass(frozen=True)
class DriftEvent:
    detected_at: datetime
    kind: str
    target: str
    field: str
    expected: Any
    observed: Any


_NOT_FOUND = object()


class DriftTracker:
    def __init__(self, grace: timedelta = DEFAULT_GRACE) -> None:
        self._grace = grace
        self._armed: dict[str, DriftIntent] = {}
        self._events: deque[DriftEvent] = deque(maxlen=EVENT_HISTORY)
        self._count = 0

    @property
    def grace(self) -> timedelta:
        return self._grace

    @property
    def armed_count(self) -> int:
        return len(self._armed)

    @property
    def drift_count(self) -> int:
        return self._count

    @property
    def last_drift_at(self) -> datetime | None:
        return self._events[-1].detected_at if self._events else None

    def recent_events(self) -> list[DriftEvent]:
        return list(self._events)

    def arm(self, intents: Iterable[DriftIntent]) -> None:
        for intent in intents:
            self._armed[intent.intent_id] = intent

    def observe(
        self,
        snapshot: TelemetrySnapshot,
        *,
        now: datetime | None = None,
    ) -> list[DriftEvent]:
        """Evaluate all armed intents against `snapshot`.

        Returns the list of DriftEvents recorded on this call (empty
        when nothing fired). Disarms each intent that either matched or
        timed out so a single intent never fires twice.
        """
        if not self._armed:
            return []
        if now is None:
            now = datetime.now(timezone.utc)
        fired: list[DriftEvent] = []
        disarm: list[str] = []
        for intent in self._armed.values():
            observed = _observed_value(snapshot, intent)
            if observed is _NOT_FOUND:
                # Target not present in this snapshot — leave armed
                # until grace expires, then disarm without firing (we
                # can't distinguish a legitimate absent zone from drift).
                if now - intent.armed_at >= self._grace:
                    disarm.append(intent.intent_id)
                continue
            if observed == intent.expected:
                disarm.append(intent.intent_id)
                continue
            if now - intent.armed_at < self._grace:
                continue
            event = DriftEvent(
                detected_at=now,
                kind=intent.kind,
                target=intent.target,
                field=intent.field,
                expected=intent.expected,
                observed=observed,
            )
            self._events.append(event)
            self._count += 1
            fired.append(event)
            disarm.append(intent.intent_id)
            logger.warning(
                "drift: %s on %s expected %s=%r but telemetry reports %r",
                intent.kind, intent.target, intent.field,
                intent.expected, observed,
            )
        for iid in disarm:
            self._armed.pop(iid, None)
        return fired


def _observed_value(snapshot: TelemetrySnapshot, intent: DriftIntent) -> Any:
    if intent.target.startswith("zones/"):
        zone_id = intent.target.split("/", 1)[1]
        for z in snapshot.zones:
            if z.id == zone_id:
                return getattr(z, intent.field, _NOT_FOUND)
        return _NOT_FOUND
    return getattr(snapshot, intent.field, _NOT_FOUND)


def _make_intent(
    kind: str,
    target: str,
    field: str,
    expected: Any,
    *,
    now: datetime,
) -> DriftIntent:
    return DriftIntent(
        intent_id=uuid.uuid4().hex,
        kind=kind,
        target=target,
        field=field,
        expected=expected,
        armed_at=now,
    )


def intents_for_mutation(
    kind: str,
    payload: dict,
    *,
    now: datetime | None = None,
) -> list[DriftIntent]:
    """Build DriftIntents for a mutation's payload.

    MVP kinds only — everything else returns [] and is tracked as a
    backlog item for per-kind signal design.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    zone_id = payload.get("zone_id")
    if kind == "zone_setpoints_set":
        if zone_id is None:
            return []
        target = f"zones/{zone_id}"
        out: list[DriftIntent] = []
        if payload.get("cool") is not None:
            out.append(_make_intent(
                kind, target, "coolSetpoint", int(payload["cool"]), now=now
            ))
        if payload.get("heat") is not None:
            out.append(_make_intent(
                kind, target, "heatSetpoint", int(payload["heat"]), now=now
            ))
        # activate_hold defaults to True at the API layer; only False
        # means "stage the setpoints without engaging hold."
        if payload.get("activate_hold", True) is not False:
            out.append(_make_intent(
                kind, target, "holdActive", True, now=now
            ))
        return out
    if kind == "zone_hold_set":
        if zone_id is None:
            return []
        return [_make_intent(
            kind, f"zones/{zone_id}", "holdActive", True, now=now
        )]
    if kind == "zone_hold_clear":
        if zone_id is None:
            return []
        return [_make_intent(
            kind, f"zones/{zone_id}", "holdActive", False, now=now
        )]
    return []
