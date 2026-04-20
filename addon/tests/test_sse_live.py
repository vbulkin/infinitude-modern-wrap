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


def test_sse_delivers_notification_over_wire(live_server):
    store, base_url = live_server
    body = (FIXTURES / "change_opmode_notifications.xml").read_bytes()
    delivered: dict = {}
    reader_ready = threading.Event()

    def _read_stream() -> None:
        with httpx.stream("GET", f"{base_url}/v1/events", timeout=10.0) as r:
            reader_ready.set()
            event_name: str | None = None
            for line in r.iter_lines():
                if line.startswith("event:"):
                    event_name = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and event_name == "notification":
                    delivered.update(json.loads(line.split(":", 1)[1].strip()))
                    return

    reader = threading.Thread(target=_read_stream, daemon=True)
    reader.start()
    assert reader_ready.wait(timeout=3.0), "reader never opened the stream"

    # Wait for the server-side handler to register its subscription.
    for _ in range(200):
        if store.subscriber_count >= 1:
            break
        time.sleep(0.01)
    assert store.subscriber_count >= 1, "SSE subscription never registered"

    resp = httpx.post(
        f"{base_url}/systems/0000TEST0000/notifications",
        content=body,
        headers={"content-type": "application/xml"},
        timeout=5.0,
    )
    assert resp.status_code == 200

    reader.join(timeout=5.0)
    assert delivered, "notification frame not delivered on the stream"
    assert delivered["serial"] == "0000TEST0000"
    assert delivered["event"]["changes"][0]["id"] == "OP_MODE"
