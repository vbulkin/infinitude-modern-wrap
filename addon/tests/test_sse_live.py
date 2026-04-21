"""SSE integration test against a live uvicorn server.

TestClient and httpx.ASGITransport both buffer a full response before
returning — neither can exercise an endpoint that never closes. This
test spins up uvicorn on an ephemeral port in a background thread and
hits the wire so the SSE frame actually round-trips.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from infinitude_proxy.main import create_app
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read_one_event(lines) -> dict:
    """Collect one complete SSE frame from a line iterator.

    An SSE frame ends at a blank line — we gather `id:`, `event:` and
    `data:` prefixed lines until that separator, then return the parsed
    data plus metadata. Caller passes the iterator (not the response)
    so a sequence of reads shares iteration state.
    """
    eid: str | None = None
    name: str | None = None
    data: str | None = None
    for line in lines:
        if line == "":
            if name is not None:
                return {"id": eid, "event": name, "data": data}
            continue
        if line.startswith("id:"):
            eid = line.split(":", 1)[1].strip()
        elif line.startswith("event:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
    raise RuntimeError("stream ended before a complete frame")


def _free_port() -> int:
    """Grab a free port from the kernel.

    Brief race: we release the socket before uvicorn re-binds. Tolerable
    for a local test; if this ever flakes, pre-bind the socket and pass
    it to uvicorn via the Config.fd path instead.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server():
    store = StateStore()
    app = create_app(store=store)
    port = _free_port()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", lifespan="off"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 5.0
    while time.time() < deadline and not server.started:
        time.sleep(0.02)
    if not server.started:
        raise RuntimeError("uvicorn did not come up within 5s")

    try:
        yield store, f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)


def test_sse_delivers_state_update_over_wire(live_server):
    """Telemetry POST → `state.update` event reaches a live SSE client.

    Replaces the old notification-SSE test: the spec's EventEnvelope
    enum is state/hold/health, so raw thermostat notifications are no
    longer broadcast on /v1/events (they remain on /v1/notifications).
    This test asserts the same end-to-end path for the new event shape.
    """
    store, base_url = live_server
    body = (FIXTURES / "telemetry_steady.xml").read_bytes()
    collected: list[dict] = []
    reader_ready = threading.Event()

    def _read_stream() -> None:
        with httpx.stream("GET", f"{base_url}/v1/events", timeout=10.0) as r:
            reader_ready.set()
            lines = r.iter_lines()
            # First frame is the on-connect snapshot.
            snap = _read_one_event(lines)
            collected.append(snap)
            # Next frame is the telemetry-triggered state.update.
            upd = _read_one_event(lines)
            collected.append(upd)

    reader = threading.Thread(target=_read_stream, daemon=True)
    reader.start()
    assert reader_ready.wait(timeout=3.0), "reader never opened the stream"

    for _ in range(200):
        if store.subscriber_count >= 1:
            break
        time.sleep(0.01)
    assert store.subscriber_count >= 1, "SSE subscription never registered"

    resp = httpx.post(
        f"{base_url}/systems/0000TEST0000/status",
        content=body,
        headers={"content-type": "application/xml"},
        timeout=5.0,
    )
    assert resp.status_code == 200

    reader.join(timeout=5.0)
    assert len(collected) == 2, "expected snapshot + state.update frames"
    snap, upd = collected
    assert snap["event"] == "state.snapshot"
    assert snap["id"] is not None
    assert upd["event"] == "state.update"
    data = json.loads(upd["data"])
    assert data["resource"] == "system"
