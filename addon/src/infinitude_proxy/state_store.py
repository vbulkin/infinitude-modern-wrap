"""In-memory state store.

Holds the latest telemetry snapshot, the wall-clock time it landed,
and the serial of the thermostat that sent it. Written under an
asyncio.Lock so concurrent southbound POSTs and northbound reads can
never observe a torn snapshot.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from .parser import NotificationEvent, SystemConfig, TelemetrySnapshot

NOTIFICATION_BUFFER_SIZE = 50


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


class StateStore:
    def __init__(self) -> None:
        self._telemetry: StoredTelemetry | None = None
        self._config: StoredConfig | None = None
        self._notifications: deque[StoredNotification] = deque(
            maxlen=NOTIFICATION_BUFFER_SIZE
        )
        self._config_dirty: bool = False
        self._lock = asyncio.Lock()

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

    async def mark_config_dirty(self) -> None:
        """Signal to the next telemetry directive that the thermostat
        should re-fetch its config. Cleared by the next apply_config."""
        async with self._lock:
            self._config_dirty = True

    async def append_notifications(
        self, serial: str, events: list[NotificationEvent]
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            for ev in events:
                self._notifications.append(
                    StoredNotification(serial=serial, event=ev, receivedAt=now)
                )

    def get_telemetry(self) -> StoredTelemetry | None:
        return self._telemetry

    def get_config(self) -> StoredConfig | None:
        return self._config

    def recent_notifications(self) -> list[StoredNotification]:
        return list(self._notifications)

    @property
    def config_dirty(self) -> bool:
        return self._config_dirty
