"""In-memory state store.

Holds the latest telemetry snapshot, the wall-clock time it landed,
and the serial of the thermostat that sent it. Written under an
asyncio.Lock so concurrent southbound POSTs and northbound reads can
never observe a torn snapshot.

When a Persistence handle is attached, config/idu/odu writes and the
dirty flag are mirrored to SQLite so a proxy restart rehydrates the
same view the thermostat last sent. Telemetry is intentionally *not*
persisted — it refreshes every ~12–20 s and the thermostat's next POST
supersedes any stored copy within the pingRate window.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from typing import Callable

from lxml import etree

from .drift import DriftTracker, intents_for_mutation
from .events import EventPublisher
from .models import Energy, EquipmentEvents, IduConfig, OduConfig
from .mutations import REPLAY_REGISTRY
from .parser import (
    NotificationEvent,
    SystemConfig,
    TelemetrySnapshot,
    parse_idu_config,
    parse_odu_config,
    parse_system_config_with_tree,
    reparse_config_tree,
    serialize_config_tree,
)
from .persistence import Persistence

logger = logging.getLogger(__name__)

NOTIFICATION_BUFFER_SIZE = 50

# Mutation kinds that represent a hold transition. For these, mutate_config
# emits a `hold.changed` event in addition to the usual `state.update`.
_HOLD_SET_KINDS = {"zone_hold_set", "system_hold_set"}
_HOLD_CLEAR_KINDS = {"zone_hold_clear", "system_hold_clear"}


def _target_to_resource(target: str | None) -> str:
    """Translate mutate_config's internal `target` to an SSE resource path.

    Targets use colon-separated dotted paths (e.g. `zone:1:schedule`);
    the spec wants slash-separated with pluralized collections
    (e.g. `zones/1/schedule`, `system/vacation`). Collisions aren't
    possible because target components never contain slashes or colons.
    """
    if not target:
        return "system"
    parts = target.split(":")
    out: list[str] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if p == "zone" and i + 1 < len(parts):
            out.append(f"zones/{parts[i + 1]}")
            i += 2
            continue
        if p == "activity" and i + 1 < len(parts):
            out.append(f"activities/{parts[i + 1]}")
            i += 2
            continue
        if p in ("vacation", "humidity", "service") and not out:
            out.append(f"system/{p}")
            i += 1
            continue
        out.append(p)
        i += 1
    return "/".join(out)


def _sanitize_changes(kind: str, payload: dict) -> dict:
    """Strip routing keys from `payload` so `changes` only has user fields.

    `zone_id`, `activity_id`, and `activate_hold` are dispatch parameters
    for the mutation function — they identify the target resource or
    control side-effects, not the values the client set. Removing them
    keeps SSE consumers from thinking the thermostat changed identity.
    """
    drop = {"zone_id", "activity_id", "activate_hold"}
    return {k: v for k, v in payload.items() if k not in drop}


@dataclass
class StoredTelemetry:
    serial: str
    snapshot: TelemetrySnapshot
    receivedAt: datetime


@dataclass
class StoredConfig:
    serial: str
    config: SystemConfig
    tree: etree._Element
    receivedAt: datetime


@dataclass
class StoredNotification:
    serial: str
    event: NotificationEvent
    receivedAt: datetime


@dataclass
class StoredIdu:
    serial: str
    config: IduConfig
    receivedAt: datetime


@dataclass
class StoredOdu:
    serial: str
    config: OduConfig
    receivedAt: datetime


@dataclass
class StoredEnergy:
    serial: str
    energy: "Energy"
    receivedAt: datetime


@dataclass
class StoredEquipmentEvents:
    serial: str
    events: "EquipmentEvents"
    receivedAt: datetime


class StateStore:
    def __init__(self, persistence: Persistence | None = None) -> None:
        self._telemetry: StoredTelemetry | None = None
        self._config: StoredConfig | None = None
        self._idu: StoredIdu | None = None
        self._odu: StoredOdu | None = None
        # Latest energy snapshot + equipment-events list. Both are
        # POSTed sporadically by the thermostat (energy ~daily,
        # events on-demand when faults are observed). In-memory only —
        # not persisted, since they're snapshot-style and the next
        # POST supersedes them.
        self._energy: StoredEnergy | None = None
        self._equipment_events: StoredEquipmentEvents | None = None
        self._notifications: deque[StoredNotification] = deque(
            maxlen=NOTIFICATION_BUFFER_SIZE
        )
        self._config_dirty: bool = False
        self._lock = asyncio.Lock()
        self._persistence = persistence
        self.events = EventPublisher()
        self.drift = DriftTracker()

    def attach_persistence(self, persistence: Persistence | None) -> None:
        """Attach (or detach) the persistence handle after construction.

        Used by the FastAPI lifespan: the store is built synchronously
        at create_app() time, but the aiosqlite connection can only be
        opened inside an event loop at startup. Safe to call with None
        to detach (e.g. when persistence open fails and we degrade to
        in-memory-only mode)."""
        self._persistence = persistence

    async def restore_from_persistence(self) -> None:
        """Rehydrate in-memory state from the most recent DB snapshot.

        Called once on app startup, before any southbound POST has
        landed. No-op when persistence isn't attached or the DB is
        empty. Single-unit assumption: we load the latest row across
        all serials (load_any) rather than requiring the serial up
        front — the thermostat's next telemetry POST will confirm it.
        A parse failure on any cached XML is logged and skipped so a
        corrupted blob can't block startup.
        """
        if self._persistence is None:
            return
        snap = await self._persistence.load_any()
        if snap is None:
            return
        received = datetime.fromtimestamp(snap.updated_at, tz=timezone.utc)
        async with self._lock:
            if snap.config_xml is not None:
                try:
                    tree, config = parse_system_config_with_tree(snap.config_xml)
                    self._config = StoredConfig(
                        serial=snap.serial,
                        config=config,
                        tree=tree,
                        receivedAt=received,
                    )
                except Exception:
                    logger.exception(
                        "state_store: failed to restore config_xml for %s",
                        snap.serial,
                    )
            if snap.idu_xml is not None:
                try:
                    self._idu = StoredIdu(
                        serial=snap.serial,
                        config=parse_idu_config(snap.idu_xml),
                        receivedAt=received,
                    )
                except Exception:
                    logger.exception(
                        "state_store: failed to restore idu_xml for %s",
                        snap.serial,
                    )
            if snap.odu_xml is not None:
                try:
                    self._odu = StoredOdu(
                        serial=snap.serial,
                        config=parse_odu_config(snap.odu_xml),
                        receivedAt=received,
                    )
                except Exception:
                    logger.exception(
                        "state_store: failed to restore odu_xml for %s",
                        snap.serial,
                    )
            self._config_dirty = snap.config_dirty
        logger.info(
            "state_store: restored from persistence serial=%s dirty=%s",
            snap.serial, snap.config_dirty,
        )

    async def apply_telemetry(self, serial: str, snapshot: TelemetrySnapshot) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            self._telemetry = StoredTelemetry(
                serial=serial,
                snapshot=snapshot,
                receivedAt=now,
            )
            # Evaluate drift inside the lock so a racing mutate_config
            # can't arm an intent mid-observe and then watch this same
            # (pre-arm) snapshot disarm it.
            drift_events = self.drift.observe(snapshot, now=now)
            drift_count = self.drift.drift_count
        # Empty `changes` is the re-fetch hint: telemetry touches many
        # fields and enumerating them here would duplicate the parser.
        # Clients that care replay from /v1/state on the event.
        await self.events.publish(
            "state.update", {"resource": "system", "changes": {}}
        )
        if drift_events:
            # One health.changed per batch of drift events, carrying just
            # the fired ones rather than the full recent-events ring.
            # Clients can poll /v1/healthz for the full picture on receipt.
            await self.events.publish(
                "health.changed",
                {
                    "reason": "mutation_drift",
                    "driftCount": drift_count,
                    "events": [
                        {
                            "detectedAt": ev.detected_at.isoformat(),
                            "kind": ev.kind,
                            "target": ev.target,
                            "field": ev.field,
                            "expected": str(ev.expected),
                            "observed": str(ev.observed),
                        }
                        for ev in drift_events
                    ],
                },
            )

    async def apply_config(
        self,
        serial: str,
        config: SystemConfig,
        tree: etree._Element,
    ) -> None:
        """Store a thermostat-pushed config, replaying any queued writes.

        Replay dispatcher: if pending rows exist for this serial, each
        is re-applied to `tree` via REPLAY_REGISTRY before we commit,
        so the thermostat's next GET /config round-trips our mutations
        rather than reverting them. Unknown `kind` values are logged
        and skipped — the row stays pending so a newer build that knows
        how to replay it can still catch up. `config` is re-derived
        from the mutated tree when any replay actually ran.
        """
        mutated = False
        if self._persistence is not None:
            pending = await self._persistence.pending(serial)
            for pw in pending:
                fn = REPLAY_REGISTRY.get(pw.kind)
                if fn is None:
                    logger.warning(
                        "replay: no dispatcher for kind=%s id=%d; "
                        "leaving pending", pw.kind, pw.id,
                    )
                    continue
                try:
                    fn(tree, pw.payload)
                    mutated = True
                except Exception:
                    logger.exception(
                        "replay: dispatcher %s failed on pending id=%d; "
                        "leaving pending", pw.kind, pw.id,
                    )
            if mutated:
                # Re-derive the typed snapshot so /v1/state reflects replays.
                config = reparse_config_tree(tree)
                logger.info(
                    "replay: re-applied %d pending write(s) to serial=%s",
                    len(pending), serial,
                )
        async with self._lock:
            self._config = StoredConfig(
                serial=serial,
                config=config,
                tree=tree,
                receivedAt=datetime.now(timezone.utc),
            )
            # Dirty flag is NOT cleared here. Upstream Perl Infinitude
            # clears optimistically in the status-POST handler: when we
            # signal configHasChanges=true we assume the thermostat will
            # follow up with a GET /config and flip the flag back to
            # false immediately so the next status POST doesn't re-signal.
            # See take_config_dirty() below.
            if self._persistence is not None:
                await self._try_persist(
                    self._persistence.save_config(
                        serial, serialize_config_tree(tree)
                    ),
                    what="save_config",
                )
            # If we replayed writes onto the thermostat's tree, the
            # device doesn't know about them yet — signal dirty so the
            # next directive tells it to GET /config and pick up the
            # replayed edits.
            if mutated and not self._config_dirty:
                self._config_dirty = True
                if self._persistence is not None:
                    await self._try_persist(
                        self._persistence.save_config_dirty(serial, True),
                        what="save_config_dirty",
                    )
        await self.events.publish(
            "state.update", {"resource": "system", "changes": {}}
        )

    async def mutate_config(
        self,
        fn: Callable[[etree._Element, dict], None],
        *,
        serial: str,
        kind: str,
        target: str | None,
        payload: dict,
    ) -> StoredConfig | None:
        """Apply a northbound mutation to the retained config tree.

        Holds the state lock across the full edit → persist → enqueue
        → dirty-flag sequence so a racing southbound POST can't observe
        a half-mutated tree. Returns the updated StoredConfig, or None
        if no config has been received from the thermostat yet (the
        caller's contract is to 404 in that case).

        Pending row is enqueued even though we also persist the mutated
        tree bytes: the bytes cover a proxy restart before the next
        thermostat POST, while the pending row survives a replace-tree
        operation on the thermostat-reboot race path (see apply_config
        above).
        """
        if self._config is None:
            return None
        async with self._lock:
            if self._config is None or self._config.serial != serial:
                return None
            fn(self._config.tree, payload)
            new_config = reparse_config_tree(self._config.tree)
            now = datetime.now(timezone.utc)
            self._config = StoredConfig(
                serial=serial,
                config=new_config,
                tree=self._config.tree,
                receivedAt=now,
            )
            self._config_dirty = True
            # Arm drift intents under the state lock so the next
            # telemetry tick (also under the lock) sees them.
            self.drift.arm(intents_for_mutation(kind, payload, now=now))
            if self._persistence is not None:
                await self._try_persist(
                    self._persistence.save_config(
                        serial, serialize_config_tree(self._config.tree)
                    ),
                    what="save_config",
                )
                await self._try_persist(
                    self._persistence.save_config_dirty(serial, True),
                    what="save_config_dirty",
                )
                try:
                    await self._persistence.enqueue_write(
                        serial, kind, target, payload
                    )
                except Exception:
                    # Enqueue failure is observable (pull-observed clear
                    # won't know about this write) but not fatal — the
                    # tree bytes are already persisted so a restart still
                    # serves the mutated config. Log and continue.
                    logger.exception(
                        "persistence: enqueue_write failed kind=%s target=%s",
                        kind, target,
                    )
            result = self._config
        resource = _target_to_resource(target)
        await self.events.publish(
            "state.update",
            {"resource": resource, "changes": _sanitize_changes(kind, payload)},
        )
        if kind in _HOLD_SET_KINDS or kind in _HOLD_CLEAR_KINDS:
            hold_resource = (
                f"{resource}/hold" if not resource.endswith("/hold") else resource
            )
            hold_payload: dict = {
                "resource": hold_resource,
                "state": "active" if kind in _HOLD_SET_KINDS else "cleared",
            }
            if "activity" in payload and payload["activity"]:
                hold_payload["activity"] = payload["activity"]
            if "otmr" in payload:
                hold_payload["until"] = payload["otmr"] or None
            await self.events.publish("hold.changed", hold_payload)
        return result

    async def apply_idu(
        self,
        serial: str,
        config: IduConfig,
        *,
        raw_xml: bytes | None = None,
    ) -> None:
        async with self._lock:
            self._idu = StoredIdu(
                serial=serial,
                config=config,
                receivedAt=datetime.now(timezone.utc),
            )
            if self._persistence is not None and raw_xml is not None:
                await self._try_persist(
                    self._persistence.save_idu(serial, raw_xml),
                    what="save_idu",
                )

    async def apply_odu(
        self,
        serial: str,
        config: OduConfig,
        *,
        raw_xml: bytes | None = None,
    ) -> None:
        async with self._lock:
            self._odu = StoredOdu(
                serial=serial,
                config=config,
                receivedAt=datetime.now(timezone.utc),
            )
            if self._persistence is not None and raw_xml is not None:
                await self._try_persist(
                    self._persistence.save_odu(serial, raw_xml),
                    what="save_odu",
                )

    async def apply_energy(self, serial: str, energy: Energy) -> None:
        """Replace the stored `<energy>` snapshot. Not persisted —
        thermostat re-posts every ~24 h and the previous one becomes
        stale anyway."""
        async with self._lock:
            self._energy = StoredEnergy(
                serial=serial, energy=energy,
                receivedAt=datetime.now(timezone.utc),
            )

    async def apply_equipment_events(
        self, serial: str, events: EquipmentEvents,
    ) -> None:
        """Replace the stored fault list. The thermostat sends the
        full list on each POST (not deltas), so a straight overwrite
        matches its semantics."""
        async with self._lock:
            self._equipment_events = StoredEquipmentEvents(
                serial=serial, events=events,
                receivedAt=datetime.now(timezone.utc),
            )

    async def mark_config_dirty(self) -> None:
        """Signal to the next telemetry directive that the thermostat
        should re-fetch its config. Cleared optimistically the next time
        the status-POST handler builds a directive saying so."""
        async with self._lock:
            self._config_dirty = True
            # Persist under the same lock so a racing apply_config can't
            # swap `_config` to a different serial between our read and
            # the disk write. Harmless for single-unit deploys; matters
            # once multi-thermostat lands.
            if self._persistence is not None and self._config is not None:
                await self._try_persist(
                    self._persistence.save_config_dirty(
                        self._config.serial, True
                    ),
                    what="save_config_dirty",
                )

    async def take_config_dirty(self) -> bool:
        """Atomically read the dirty flag and clear it.

        Called by the status-POST handler: if this returns True, the
        outgoing directive says configHasChanges=true and we've already
        flipped the flag back to false. The thermostat is expected to
        follow up with GET /systems/{serial}/config to pick up the
        mutated tree. If that GET never arrives (crash, network loss),
        the pending edit is lost — matching upstream Perl's trade-off.

        Persistence write happens under the same lock as the flag flip,
        so a concurrent apply_config can't change `_config.serial`
        between our read of it and the disk write.
        """
        async with self._lock:
            was_dirty = self._config_dirty
            self._config_dirty = False
            if was_dirty and self._persistence is not None and self._config is not None:
                await self._try_persist(
                    self._persistence.save_config_dirty(
                        self._config.serial, False
                    ),
                    what="save_config_dirty",
                )
        return was_dirty

    async def _try_persist(self, coro, *, what: str) -> None:
        """Await a persistence coroutine, swallowing failures.

        Rationale: in-memory state has already been updated by the time
        we call this. A SQLite write failure (disk full, permission
        change, WAL lock timeout) shouldn't propagate out to the
        southbound handler and return a 500 to the thermostat — that
        would desync the directive channel and risk a retry storm.
        Degraded behavior (memory ahead of disk) is recovered on next
        successful write; if the process dies before that we lose the
        single update, same as if persistence had never been configured.
        """
        try:
            await coro
        except Exception:
            logger.exception("persistence: %s failed; continuing in-memory", what)

    async def append_notifications(
        self, serial: str, events: list[NotificationEvent]
    ) -> None:
        """Append thermostat notifications to the ring buffer + publish
        on the SSE stream so live consumers (HA, browsers) see them
        without polling the REST endpoint.

        Notifications are coarse-grained — one POST may carry several
        events (fault clear + new fault, etc.) — so we batch them into
        one `notifications.received` SSE event with `count` and the
        full event list. INFO log records arrival so the operator can
        see notifications in `journalctl`/Apps log without arming
        capture.
        """
        if not events:
            return
        now = datetime.now(timezone.utc)
        async with self._lock:
            for ev in events:
                sn = StoredNotification(serial=serial, event=ev, receivedAt=now)
                self._notifications.append(sn)
        # Summarize for the INFO log — first event's class + count,
        # truncated. The full event list is in the SSE payload below
        # (and on /v1/notifications) for anyone who needs it.
        first = events[0]
        first_summary = (
            getattr(first, "eventClass", None)
            or getattr(first, "type", None)
            or type(first).__name__
        )
        logger.info(
            "notification: serial=%s count=%d first=%s",
            serial, len(events), first_summary,
        )
        await self.events.publish(
            "notifications.received",
            {
                "serial": serial,
                "count": len(events),
                "events": [
                    ev.model_dump(mode="json") if hasattr(ev, "model_dump") else dict(ev)
                    for ev in events
                ],
            },
        )

    @property
    def subscriber_count(self) -> int:
        return self.events.subscriber_count

    def get_telemetry(self) -> StoredTelemetry | None:
        return self._telemetry

    def get_config(self) -> StoredConfig | None:
        return self._config

    def get_energy(self) -> StoredEnergy | None:
        return self._energy

    def get_equipment_events(self) -> StoredEquipmentEvents | None:
        return self._equipment_events

    def get_idu(self) -> StoredIdu | None:
        return self._idu

    def get_odu(self) -> StoredOdu | None:
        return self._odu

    def recent_notifications(self) -> list[StoredNotification]:
        return list(self._notifications)

    @property
    def config_dirty(self) -> bool:
        return self._config_dirty

    @property
    def persistence(self) -> Persistence | None:
        """Expose the attached DB handle for readers that need direct
        access (healthz aggregates pending-write counts, Slice 2's
        mutate_config helper will enqueue writes). None when the proxy
        is running in in-memory-only mode (test fixtures, open failure)."""
        return self._persistence
