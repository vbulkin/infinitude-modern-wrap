"""In-memory state store.

Holds the latest telemetry snapshot, the wall-clock time it landed,
and the serial of the thermostat that sent it. Written under an
asyncio.Lock so concurrent southbound POSTs and northbound reads can
never observe a torn snapshot.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from .parser import SystemConfig, TelemetrySnapshot


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


class StateStore:
    def __init__(self) -> None:
        self._telemetry: StoredTelemetry | None = None
        self._config: StoredConfig | None = None
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

    def get_telemetry(self) -> StoredTelemetry | None:
        return self._telemetry

    def get_config(self) -> StoredConfig | None:
        return self._config
