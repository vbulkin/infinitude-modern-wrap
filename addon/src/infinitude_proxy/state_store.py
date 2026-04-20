"""In-memory state store.

Holds the latest telemetry snapshot, the wall-clock time it landed,
and the serial of the thermostat that sent it. Written under an
asyncio.Lock so concurrent southbound POSTs and northbound reads can
never observe a torn snapshot.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import IduConfig, OduConfig
from .parser import NotificationEvent, SystemConfig, TelemetrySnapshot

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
    def __init__(self) -> None:
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

    async def apply_telemetry(self, serial: str, snapshot: TelemetrySnapshot) -> None:
        async with self._lock:
            self._telemetry = StoredTelemetry(
                serial=serial,
                snapshot=snapshot,
                receivedAt=datetime.now(timezone.utc),
            )

    async def apply_config(self, serial: str, config: SystemConfig) -> None:
        async with self._lock:
            self._config = StoredConfig(
                serial=serial,
                config=config,
                receivedAt=datetime.now(timezone.utc),
            )
            # Fresh config from the thermostat — whatever northbound edits
            # were pending have now been round-tripped. Clear the flag.
            self._config_dirty = False

    async def apply_idu(self, serial: str, config: IduConfig) -> None:
        async with self._lock:
            self._idu = StoredIdu(
                serial=serial,
                config=config,
                receivedAt=datetime.now(timezone.utc),
            )

    async def apply_odu(self, serial: str, config: OduConfig) -> None:
        async with self._lock:
            self._odu = StoredOdu(
                serial=serial,
                config=config,
                receivedAt=datetime.now(timezone.utc),
            )

    async def mark_config_dirty(self) -> None:
        """Signal to the next telemetry directive that the thermostat
        should re-fetch its config. Cleared by the next apply_config."""
        async with self._lock:
            self._config_dirty = True

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
