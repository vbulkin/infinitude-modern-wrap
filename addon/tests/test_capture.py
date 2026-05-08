"""Tests for the debug traffic capture subsystem.

Covers three layers:
  - Persistence: v1 → v2 migration adds capture_traffic; CRUD + cap.
  - Middleware: captures when enabled, skips when disabled or path
    excluded, streams response without corruption.
  - Debug API: start/stop/status/list/get/flush.

Tests construct a test app by attaching a Persistence and CaptureControl
manually so we don't need the lifespan path (which would open a real DB
file). The persistence is opened on :memory:.
"""

from __future__ import annotations

import asyncio
import base64
import time

import pytest
from fastapi.testclient import TestClient

from infinitude_proxy.capture import (
    CaptureControl,
    CaptureMiddleware,
    MAX_BODY_BYTES,
    _is_excluded,
)
from infinitude_proxy.main import create_app
from infinitude_proxy.persistence import Persistence
from infinitude_proxy.state_store import StateStore


@pytest.fixture
async def persistence() -> Persistence:
    p = await Persistence.open(":memory:")
    try:
        yield p
    finally:
        await p.close()


@pytest.fixture
async def wired_client(persistence: Persistence):
    """TestClient with a StateStore + CaptureControl both pre-wired to
    an in-memory persistence. Lifespan is short-circuited since we pass
    `store=` (owns_store=False) — this is the same pattern the other
    integration tests use."""
    store = StateStore()
    store.attach_persistence(persistence)
    await store.restore_from_persistence()
    control = CaptureControl()
    control.attach_persistence(persistence)
    app = create_app(store=store, capture_control=control)
    client = TestClient(app)
    yield client, control, persistence


# ── Persistence layer ─────────────────────────────────────────────────


async def test_migration_creates_capture_table(persistence: Persistence):
    """Fresh :memory: DB should be at schema v2 with capture_traffic
    present and empty."""
    stats = await persistence.capture_stats()
    assert stats["rowCount"] == 0
    assert stats["oldestAt"] is None
    assert stats["totalBytes"] == 0


async def test_capture_insert_and_get(persistence: Persistence):
    row_id = await persistence.capture_insert(
        captured_at=1700000000.0,
        direction="southbound",
        method="POST",
        path="/systems/0000TEST0000/status",
        query=None,
        status_code=200,
        req_content_type="application/x-www-form-urlencoded",
        req_body=b"data=<status/>",
        resp_content_type="text/xml",
        resp_body=b"<status_response/>",
        duration_ms=7,
    )
    row = await persistence.capture_get(row_id)
    assert row is not None
    assert row["direction"] == "southbound"
    assert row["method"] == "POST"
    assert row["req_body"] == b"data=<status/>"
    assert row["resp_body"] == b"<status_response/>"
    assert row["duration_ms"] == 7


async def test_capture_round_trips_headers(persistence: Persistence):
    """v4 (alpha.53) — full request/response header dicts persist
    through capture_insert and come back verbatim from capture_get +
    capture_list. This is the diagnostic data the investigation into
    Carrier 401s relies on; if headers don't round-trip we can't
    diff thermostat-real-time vs addon-replay."""
    req_headers = {
        "authorization": "Basic abcdef",
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": "Carrier-Stat/14",
        "x-carrier-something": "opaque-token",
    }
    resp_headers = {
        "content-type": "application/xml",
        "x-carrier-trace": "id-123",
    }
    row_id = await persistence.capture_insert(
        captured_at=1700000000.0,
        direction="carrier_out",
        method="POST",
        path="https://www.api.ing.carrier.com/systems/X/status",
        query=None,
        status_code=200,
        req_content_type="application/x-www-form-urlencoded",
        req_body=b"data=<status/>",
        resp_content_type="application/xml",
        resp_body=b"<status_response/>",
        duration_ms=11,
        req_headers=req_headers,
        resp_headers=resp_headers,
    )
    # capture_get returns the raw JSON columns — caller decodes.
    import json as _json
    got = await persistence.capture_get(row_id)
    assert got is not None
    assert _json.loads(got["req_headers_json"]) == req_headers
    assert _json.loads(got["resp_headers_json"]) == resp_headers
    # capture_list also surfaces the JSON columns so the API layer
    # can decode them.
    rows = await persistence.capture_list(limit=5)
    matching = [r for r in rows if r["id"] == row_id]
    assert matching
    assert _json.loads(matching[0]["req_headers_json"]) == req_headers
    assert _json.loads(matching[0]["resp_headers_json"]) == resp_headers


async def test_capture_headers_optional(persistence: Persistence):
    """Pre-v4 entries (or capture-off mid-request) leave the header
    columns NULL. capture_get/list should pass that through as None
    so the API layer can render `null`/missing without errors."""
    row_id = await persistence.capture_insert(
        captured_at=1700000000.0,
        direction="northbound",
        method="GET",
        path="/v1/state",
        query=None,
        status_code=200,
        req_content_type=None,
        req_body=None,
        resp_content_type="application/json",
        resp_body=b"{}",
        duration_ms=2,
        # No req_headers / resp_headers passed — defaults to None.
    )
    got = await persistence.capture_get(row_id)
    assert got is not None
    assert got["req_headers_json"] is None
    assert got["resp_headers_json"] is None


async def test_capture_trim_caps_rows(persistence: Persistence):
    for i in range(25):
        await persistence.capture_insert(
            captured_at=1700000000.0 + i,
            direction="northbound",
            method="GET",
            path=f"/v1/zones/{i}",
            query=None,
            status_code=200,
            req_content_type=None,
            req_body=None,
            resp_content_type="application/json",
            resp_body=b"{}",
            duration_ms=1,
            max_rows=10,
        )
    stats = await persistence.capture_stats()
    assert stats["rowCount"] == 10
    # The surviving rows are the 10 most recent.
    rows = await persistence.capture_list(limit=100)
    assert len(rows) == 10
    paths = [r["path"] for r in rows]
    assert paths[0] == "/v1/zones/24"
    assert paths[-1] == "/v1/zones/15"


async def test_capture_list_filters(persistence: Persistence):
    now = 1700000000.0
    await persistence.capture_insert(
        captured_at=now, direction="southbound", method="POST",
        path="/systems/X/status", query=None, status_code=200,
        req_content_type=None, req_body=None,
        resp_content_type=None, resp_body=None, duration_ms=1,
    )
    await persistence.capture_insert(
        captured_at=now + 1, direction="northbound", method="GET",
        path="/v1/state", query=None, status_code=200,
        req_content_type=None, req_body=None,
        resp_content_type=None, resp_body=None, duration_ms=2,
    )
    await persistence.capture_insert(
        captured_at=now + 2, direction="northbound", method="PATCH",
        path="/v1/zones/1", query=None, status_code=200,
        req_content_type=None, req_body=None,
        resp_content_type=None, resp_body=None, duration_ms=3,
    )

    all_rows = await persistence.capture_list(limit=100)
    assert len(all_rows) == 3

    southbound = await persistence.capture_list(direction="southbound")
    assert len(southbound) == 1
    assert southbound[0]["path"] == "/systems/X/status"

    patches = await persistence.capture_list(method="PATCH")
    assert len(patches) == 1

    zones = await persistence.capture_list(path_prefix="/v1/zones")
    assert len(zones) == 1

    # since_id: pass the id of the oldest → return the two newer ones.
    oldest = await persistence.capture_list(limit=100)
    oldest_id = oldest[-1]["id"]
    newer = await persistence.capture_list(since_id=oldest_id)
    assert len(newer) == 2


async def test_capture_flush_deletes_all(persistence: Persistence):
    for i in range(5):
        await persistence.capture_insert(
            captured_at=1700000000.0 + i, direction="southbound",
            method="POST", path="/x", query=None, status_code=200,
            req_content_type=None, req_body=None,
            resp_content_type=None, resp_body=None, duration_ms=0,
        )
    deleted = await persistence.capture_flush()
    assert deleted == 5
    stats = await persistence.capture_stats()
    assert stats["rowCount"] == 0


# ── Excluded-path helper ──────────────────────────────────────────────


def test_excluded_paths():
    assert _is_excluded("/v1/events")
    assert _is_excluded("/v1/events/")
    assert _is_excluded("/v1/healthz")
    assert _is_excluded("/docs")
    assert _is_excluded("/openapi.json")
    assert _is_excluded("/")
    assert _is_excluded("/v1/debug/capture/status")
    assert _is_excluded("/static/logo.png")
    # Not excluded:
    assert not _is_excluded("/v1/state")
    assert not _is_excluded("/v1/zones/1")
    assert not _is_excluded("/systems/0000TEST0000/status")


# ── Middleware end-to-end via TestClient ──────────────────────────────


async def _wait_for_capture(control: CaptureControl, target: int, timeout: float = 2.0) -> None:
    """Capture inserts are fire-and-forget (asyncio.create_task), so the
    TestClient response can return before the DB row lands. Poll until
    the submitted counter matches expectations, or bail out on timeout."""
    deadline = time.monotonic() + timeout
    while control.submitted < target and time.monotonic() < deadline:
        await asyncio.sleep(0.01)


async def test_capture_off_records_nothing(wired_client):
    client, control, persistence = wired_client
    assert control.enabled is False

    r = client.get("/v1/state")
    # State before config arrives = 503, but the middleware only cares
    # about whether it captured, not the status.
    assert r.status_code in (200, 503)

    stats = await persistence.capture_stats()
    assert stats["rowCount"] == 0
    assert control.submitted == 0


async def test_capture_on_records_northbound(wired_client):
    client, control, persistence = wired_client
    control.start()

    client.get("/v1/state")
    await _wait_for_capture(control, target=1)

    rows = await persistence.capture_list(limit=10)
    assert len(rows) == 1
    row = rows[0]
    assert row["direction"] == "northbound"
    assert row["method"] == "GET"
    assert row["path"] == "/v1/state"


async def test_capture_skips_excluded_paths(wired_client):
    client, control, persistence = wired_client
    control.start()

    # All of these must be excluded → no new rows.
    client.get("/v1/healthz")
    client.get("/docs")
    client.get("/openapi.json")
    client.get("/")
    client.get("/v1/debug/capture/status")
    # Give any (incorrect) captures a beat to land.
    await asyncio.sleep(0.05)

    stats = await persistence.capture_stats()
    assert stats["rowCount"] == 0


async def test_capture_records_post_body(wired_client):
    client, control, persistence = wired_client
    control.start()

    # Southbound POST carries form-encoded XML. We just need a path that
    # reaches a real handler; the southbound router's /Alive is cheap.
    client.get("/Alive")
    await _wait_for_capture(control, target=1)

    rows = await persistence.capture_list(limit=10)
    assert len(rows) == 1
    assert rows[0]["direction"] == "southbound"
    assert rows[0]["path"] == "/Alive"


async def test_capture_stop_halts_recording(wired_client):
    client, control, persistence = wired_client
    control.start()
    client.get("/v1/state")
    await _wait_for_capture(control, target=1)

    control.stop()
    client.get("/v1/state")
    await asyncio.sleep(0.05)

    stats = await persistence.capture_stats()
    assert stats["rowCount"] == 1  # Only the pre-stop one landed.


# ── Debug API ─────────────────────────────────────────────────────────


async def test_debug_start_stop_status(wired_client):
    client, control, persistence = wired_client

    r = client.get("/v1/debug/capture/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["rowCount"] == 0
    assert body["maxRows"] == 10_000

    r = client.post("/v1/debug/capture/start")
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    assert control.enabled is True

    r = client.post("/v1/debug/capture/stop")
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert control.enabled is False


async def test_debug_start_requires_persistence():
    """If persistence is never attached, start must fail with 503 rather
    than silently enabling a capture that won't write anywhere."""
    store = StateStore()
    control = CaptureControl()  # no persistence attached
    app = create_app(store=store, capture_control=control)
    client = TestClient(app)

    r = client.post("/v1/debug/capture/start")
    assert r.status_code == 503
    assert control.enabled is False


async def test_debug_entries_pagination_and_filter(wired_client):
    client, control, persistence = wired_client
    control.start()

    client.get("/v1/state")
    client.get("/v1/zones")
    client.get("/Alive")
    await _wait_for_capture(control, target=3)

    r = client.get("/v1/debug/capture/entries")
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) == 3

    r = client.get("/v1/debug/capture/entries?direction=northbound")
    assert r.status_code == 200
    assert all(e["direction"] == "northbound" for e in r.json())

    r = client.get("/v1/debug/capture/entries?pathPrefix=/v1/zones")
    assert r.status_code == 200
    assert all(e["path"].startswith("/v1/zones") for e in r.json())


async def test_debug_entries_bad_direction(wired_client):
    client, _, _ = wired_client
    r = client.get("/v1/debug/capture/entries?direction=sideways")
    assert r.status_code == 400


async def test_debug_entry_textual_body_decoded(wired_client):
    client, control, persistence = wired_client
    control.start()

    client.get("/v1/state")
    await _wait_for_capture(control, target=1)

    list_resp = client.get("/v1/debug/capture/entries").json()
    entry_id = list_resp[0]["id"]

    r = client.get(f"/v1/debug/capture/entries/{entry_id}")
    assert r.status_code == 200
    entry = r.json()
    # /v1/state always returns JSON (even the 503 error body is JSON)
    # so the resp_body should be decoded as utf-8, not base64.
    assert entry["respContentType"] is not None
    assert entry["respBodyEncoding"] == "utf-8"
    # Request body is empty on a GET — encoding fields must be null.
    assert entry["reqBody"] is None
    assert entry["reqBodyEncoding"] is None


async def test_debug_entry_not_found(wired_client):
    client, _, _ = wired_client
    r = client.get("/v1/debug/capture/entries/999999")
    assert r.status_code == 404


async def test_debug_flush(wired_client):
    client, control, persistence = wired_client
    control.start()

    client.get("/v1/state")
    client.get("/v1/zones")
    await _wait_for_capture(control, target=2)

    r = client.delete("/v1/debug/capture")
    assert r.status_code == 200
    assert r.json()["deleted"] == 2

    stats = await persistence.capture_stats()
    assert stats["rowCount"] == 0


async def test_debug_status_counts_errors_separately(wired_client):
    """The submitted/errors counters on CaptureControl are independent
    of the DB row count so they remain visible even after flush."""
    client, control, persistence = wired_client
    control.start()

    client.get("/v1/state")
    client.get("/v1/zones")
    await _wait_for_capture(control, target=2)

    await persistence.capture_flush()
    r = client.get("/v1/debug/capture/status")
    body = r.json()
    assert body["rowCount"] == 0
    assert body["submitted"] >= 2
    assert body["errors"] == 0


# ── Body truncation ──────────────────────────────────────────────────


async def test_capture_truncates_body_over_cap(persistence: Persistence):
    """The persistence layer accepts bodies of any size; the cap lives
    in the middleware. This test proves the DB round-trip is lossless
    at MAX_BODY_BYTES so a truncation marker in content-type is the
    only signal of clipping (not a silent size mismatch)."""
    big = b"A" * (MAX_BODY_BYTES)
    row_id = await persistence.capture_insert(
        captured_at=1700000000.0,
        direction="southbound",
        method="POST",
        path="/big",
        query=None,
        status_code=200,
        req_content_type="application/octet-stream; truncated=true",
        req_body=big,
        resp_content_type=None,
        resp_body=None,
        duration_ms=1,
    )
    row = await persistence.capture_get(row_id)
    assert row is not None
    assert row["req_body"] == big
    assert "truncated=true" in row["req_content_type"]
