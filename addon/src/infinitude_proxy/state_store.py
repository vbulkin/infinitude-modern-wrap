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

from lxml import etree

from .models import IduConfig, OduConfig
from .parser import (
    NotificationEvent,
    SystemConfig,
    TelemetrySnapshot,
    parse_idu_config,
    parse_odu_config,
    parse_system_config_with_tree,
    serialize_config_tree,
)
from .persistence import Persistence

logger = logging.getLogger(__name__)

NOTIFICATION_BUFFER_SIZE = 50
SUBSCRIBER_QUEUE_MAXSIZE = 64


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


class StateStore:
    def __init__(self, persistence: Persistence | None = None) -> None:
        self._telemetry: StoredTelemetry | None = None
        self._config: StoredConfig | None = None
        self._idu: StoredIdu | None = None
        self._odu: StoredOdu | None = None
        self._notifications: deque[StoredNotification] = deque(
            maxlen=NOTIFICATION_BUFFER_SIZE
        )
        self._config_dirty: bool = False
        self._lock = asyncio.Lock()
        self._subscribers: list[asyncio.Queue[StoredNotification]] = []
        self._persistence = persistence

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
        async with self._lock:
            self._telemetry = StoredTelemetry(
                serial=serial,
                snapshot=snapshot,
                receivedAt=datetime.now(timezone.utc),
            )

    async def apply_config(
        self,
        serial: str,
        config: SystemConfig,
        tree: etree._Element,
    ) -> None:
        # Race-fix hook: if the thermostat posts its tree while we still
        # have unapplied writes queued (e.g. proxy restart + thermostat
        # reboot interleave), Slice 2's mutate_config dispatcher will
        # re-apply each PendingWrite onto `tree` before we store it, so
        # the next GET /config round-trips our pending edits. Until that
        # dispatcher exists we just log — losing writes would be the
        # upstream Perl behavior anyway.
        if self._persistence is not None:
            pending = await self._persistence.pending(serial)
            if pending:
                logger.warning(
                    "state_store: apply_config with %d unapplied pending "
                    "write(s) for %s — replay not yet implemented (Slice 2)",
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
        now = datetime.now(timezone.utc)
        stored: list[StoredNotification] = []
        async with self._lock:
            for ev in events:
                sn = StoredNotification(serial=serial, event=ev, receivedAt=now)
                self._notifications.append(sn)
                stored.append(sn)
            subs = list(self._subscribers)
        # Broadcast outside the lock — a slow subscriber must not stall
        # the southbound POST that drove the append.
        for sn in stored:
            for q in subs:
                try:
                    q.put_nowait(sn)
                except asyncio.QueueFull:
                    # Drop: a subscriber not keeping up shouldn't cause
                    # head-of-line blocking for healthy ones. The ring
                    # buffer still has the event if they reconnect and
                    # fetch backfill later.
                    logger.warning(
                        "SSE subscriber queue full; dropping notification"
                    )

    def subscribe(self) -> asyncio.Queue[StoredNotification]:
        """Register an SSE subscriber and get its queue.

        The queue is bounded (SUBSCRIBER_QUEUE_MAXSIZE) so a stalled
        client can't grow memory without limit. Overflow drops with a
        WARNING; the caller is responsible for calling unsubscribe()
        when the stream closes (typically in a finally: block).
        """
        q: asyncio.Queue[StoredNotification] = asyncio.Queue(
            maxsize=SUBSCRIBER_QUEUE_MAXSIZE
        )
        self._subscribers.append(q)
        return q

    def unsubscribe(self, queue: asyncio.Queue[StoredNotification]) -> None:
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def get_telemetry(self) -> StoredTelemetry | None:
        return self._telemetry

    def get_config(self) -> StoredConfig | None:
        return self._config

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
