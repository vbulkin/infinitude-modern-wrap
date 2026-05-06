"""Northbound event publisher backing /v1/events (SSE).

Spec shape (openapi.yaml `EventEnvelope`): every event carries a
monotonic integer `id`, an `event` type string, and a `data` payload.
Clients resume across reconnect by sending `Last-Event-ID`; if the
requested id is still within the ring buffer we replay from there,
otherwise the caller is expected to re-seed with a `state.snapshot`.

The publisher is deliberately decoupled from the notification pipeline
(thermostat alerts still flow into a separate ring buffer served by
/v1/notifications). Notifications are not in the spec's SSE event-type
enum; keeping the two pipelines separate means we can evolve the SSE
stream without disturbing the thermostat alert path.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

EventType = Literal[
    "state.snapshot",
    "state.update",
    "health.changed",
    "hold.changed",
    # alpha.31: thermostat-side notifications (filter due, fault codes,
    # service reminders, etc.) now publish on the stream so HA-side
    # consumers can react in real-time instead of waiting up to a full
    # poll cycle for the REST endpoint at /v1/notifications. Carries
    # `{"count": N, "events": [{...}, ...]}` — count of new arrivals
    # and the parsed event list. Subscribers that only care that
    # something arrived can ignore the events array.
    "notifications.received",
]

EVENT_BUFFER_SIZE = 200
SUBSCRIBER_QUEUE_MAXSIZE = 64


@dataclass
class Event:
    id: int
    event: EventType
    data: Any


class EventPublisher:
    """Monotonic-id event broadcaster with replay buffer.

    Holds a bounded deque of recent events keyed by integer id. New
    subscribers get their own bounded queue and are fed every event
    published after subscription. A subscriber that falls behind by
    more than SUBSCRIBER_QUEUE_MAXSIZE entries is dropped from that
    event rather than blocking the publish path — the client's own
    reconnect + Last-Event-ID flow is the recovery mechanism.
    """

    def __init__(self, buffer_size: int = EVENT_BUFFER_SIZE) -> None:
        self._next_id = 1
        self._buffer: deque[Event] = deque(maxlen=buffer_size)
        self._subscribers: list[asyncio.Queue[Event]] = []
        self._lock = asyncio.Lock()

    async def publish(self, event_type: EventType, data: Any) -> Event:
        """Assign an id, buffer the event, and broadcast to subscribers.

        Returns the built Event so tests and call sites can assert on the
        assigned id without a separate fetch. Broadcast overflow drops
        the event for the affected subscriber only — publish must not
        stall on a slow consumer.
        """
        async with self._lock:
            ev = Event(id=self._next_id, event=event_type, data=data)
            self._next_id += 1
            self._buffer.append(ev)
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE subscriber queue full; dropping event id=%d type=%s",
                    ev.id, ev.event,
                )
        return ev

    def subscribe(self) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_MAXSIZE)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass

    def replay_since(self, last_id: int) -> list[Event] | None:
        """Return events with id > last_id, oldest-first.

        Returns None when `last_id` is older than the buffer's oldest
        entry — signaling the caller has missed events and must re-seed
        with a fresh `state.snapshot`. An empty list means the caller
        is caught up (their Last-Event-ID equals the latest).
        """
        if not self._buffer:
            # Empty buffer: if caller hasn't seen anything yet (0), they're
            # caught up. If they claim a higher id we haven't issued, that's
            # a client bug — treat as gap and require re-seed.
            return [] if last_id == 0 else None
        oldest = self._buffer[0].id
        if last_id < oldest - 1:
            return None
        return [ev for ev in self._buffer if ev.id > last_id]

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @property
    def latest_id(self) -> int:
        return self._next_id - 1
