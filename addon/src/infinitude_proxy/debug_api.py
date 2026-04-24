"""Debug/management API for the traffic capture subsystem.

Mounted under `/v1/debug/capture/*`. Off-by-default — `POST start`
flips the in-memory flag on the shared `CaptureControl`; the
middleware reads the flag on every request. No authentication:
mirrors the rest of the addon, which relies on HA ingress for access
control.

The router depends on a `Persistence` instance AND a `CaptureControl`;
both are passed by `main.create_app` at mount time so the route
handlers close over them. That also lets tests construct a router
against a fake persistence/control pair.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .capture import CaptureControl
from .persistence import Persistence

logger = logging.getLogger(__name__)


class CaptureStatus(BaseModel):
    enabled: bool
    maxRows: int
    rowCount: int
    oldestAt: datetime | None
    newestAt: datetime | None
    totalBytes: int
    submitted: int
    errors: int


class CaptureEntryMeta(BaseModel):
    id: int
    capturedAt: datetime
    direction: str
    method: str
    path: str
    query: str | None
    statusCode: int
    reqContentType: str | None
    reqBytes: int
    respContentType: str | None
    respBytes: int
    durationMs: int | None


class CaptureEntry(CaptureEntryMeta):
    reqBody: str | None
    reqBodyEncoding: str | None
    respBody: str | None
    respBodyEncoding: str | None


class FlushResult(BaseModel):
    deleted: int


def _iso(ts: float | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _is_textual(content_type: str | None) -> bool:
    """Decide whether a stored body can be returned as a decoded string
    or needs base64 wrapping. Text-ish content-types decode; everything
    else (octet-stream, images, binary XML) we keep raw so the caller
    sees the exact bytes."""
    if not content_type:
        return False
    ct = content_type.lower().split(";", 1)[0].strip()
    if ct.startswith("text/"):
        return True
    return ct in {
        "application/json",
        "application/xml",
        "application/x-www-form-urlencoded",
        "application/javascript",
        "application/xhtml+xml",
    }


def _encode_body(body: bytes | None, content_type: str | None) -> tuple[str | None, str | None]:
    """Return (body_string, encoding_tag) where encoding_tag is either
    'utf-8' (the body is a decoded string) or 'base64' (the body is
    base64-encoded bytes). None body → both None."""
    if body is None:
        return None, None
    if _is_textual(content_type):
        try:
            return body.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            pass
    return base64.b64encode(body).decode("ascii"), "base64"


def create_debug_router(control: CaptureControl) -> APIRouter:
    """Build the router that exposes the capture-subsystem controls.

    The shared CaptureControl carries the persistence handle; route
    handlers read it off the control rather than closing over a
    separate param so the router behaves correctly across the
    lifespan-driven attach/detach of persistence.
    """
    router = APIRouter(prefix="/v1/debug/capture", tags=["debug"])

    def _require_persistence() -> Persistence:
        if control.persistence is None:
            raise HTTPException(
                status_code=503,
                detail="persistence layer not available",
            )
        return control.persistence

    @router.post("/start", response_model=CaptureStatus)
    async def start_capture() -> CaptureStatus:
        if control.persistence is None:
            raise HTTPException(
                status_code=503,
                detail="persistence layer not available",
            )
        control.start()
        logger.info("capture: enabled")
        return await _status()

    @router.post("/stop", response_model=CaptureStatus)
    async def stop_capture() -> CaptureStatus:
        control.stop()
        logger.info("capture: disabled")
        return await _status()

    @router.get("/status", response_model=CaptureStatus)
    async def get_status() -> CaptureStatus:
        return await _status()

    async def _status() -> CaptureStatus:
        persistence = _require_persistence()
        stats = await persistence.capture_stats()
        return CaptureStatus(
            enabled=control.enabled,
            maxRows=control.max_rows,
            rowCount=stats["rowCount"],
            oldestAt=_iso(stats["oldestAt"]),
            newestAt=_iso(stats["newestAt"]),
            totalBytes=stats["totalBytes"],
            submitted=control.submitted,
            errors=control.errors,
        )

    @router.get("/entries", response_model=list[CaptureEntryMeta])
    async def list_entries(
        limit: int = Query(100, ge=1, le=1000),
        sinceId: int | None = Query(None, ge=0),
        direction: str | None = Query(None),
        method: str | None = Query(None),
        pathPrefix: str | None = Query(None),
    ) -> list[CaptureEntryMeta]:
        persistence = _require_persistence()
        if direction is not None and direction not in (
            "southbound", "northbound", "carrier_out"
        ):
            raise HTTPException(
                status_code=400,
                detail="direction must be one of: southbound, northbound, carrier_out",
            )
        rows = await persistence.capture_list(
            limit=limit,
            since_id=sinceId,
            direction=direction,
            method=method,
            path_prefix=pathPrefix,
        )
        return [
            CaptureEntryMeta(
                id=r["id"],
                capturedAt=_iso(r["captured_at"]),
                direction=r["direction"],
                method=r["method"],
                path=r["path"],
                query=r["query"],
                statusCode=r["status_code"],
                reqContentType=r["req_content_type"],
                reqBytes=int(r["req_bytes"] or 0),
                respContentType=r["resp_content_type"],
                respBytes=int(r["resp_bytes"] or 0),
                durationMs=r["duration_ms"],
            )
            for r in rows
        ]

    @router.get("/entries/{entry_id}", response_model=CaptureEntry)
    async def get_entry(entry_id: int) -> CaptureEntry:
        persistence = _require_persistence()
        row = await persistence.capture_get(entry_id)
        if row is None:
            raise HTTPException(status_code=404, detail="entry not found")
        req_str, req_enc = _encode_body(row["req_body"], row["req_content_type"])
        resp_str, resp_enc = _encode_body(row["resp_body"], row["resp_content_type"])
        return CaptureEntry(
            id=row["id"],
            capturedAt=_iso(row["captured_at"]),
            direction=row["direction"],
            method=row["method"],
            path=row["path"],
            query=row["query"],
            statusCode=row["status_code"],
            reqContentType=row["req_content_type"],
            reqBytes=len(row["req_body"]) if row["req_body"] else 0,
            respContentType=row["resp_content_type"],
            respBytes=len(row["resp_body"]) if row["resp_body"] else 0,
            durationMs=row["duration_ms"],
            reqBody=req_str,
            reqBodyEncoding=req_enc,
            respBody=resp_str,
            respBodyEncoding=resp_enc,
        )

    @router.delete("", response_model=FlushResult)
    async def flush() -> FlushResult:
        persistence = _require_persistence()
        deleted = await persistence.capture_flush()
        logger.info("capture: flushed %d rows", deleted)
        return FlushResult(deleted=deleted)

    return router
