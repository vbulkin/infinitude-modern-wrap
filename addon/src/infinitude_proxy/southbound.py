"""Southbound protocol — thermostat-facing endpoints.

These live at root (NOT under /v1/) because the thermostat firmware
ships fixed paths (`/systems/{serial}/status`, `/Alive`, etc.) and
accepts no configuration to change them. Wire format is
application/x-www-form-urlencoded with a `data` field carrying
URL-encoded XML. The response to telemetry is the "directive channel"
— three bits telling the thermostat whether to re-poll config or
server settings and at what interval.
"""

from __future__ import annotations

from urllib.parse import unquote_to_bytes

from fastapi import APIRouter, Request, Response

from .parser import parse_telemetry
from .state_store import StateStore


DIRECTIVE_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<status version="1.37">'
    b'<configHasChanges>false</configHasChanges>'
    b'<pingRate>12</pingRate>'
    b'<serverHasChanges>false</serverHasChanges>'
    b'</status>'
)


def _unwrap_form(body: bytes) -> bytes:
    if body.startswith(b"data="):
        return unquote_to_bytes(body[5:])
    return body


def create_southbound_router(store: StateStore) -> APIRouter:
    router = APIRouter(tags=["southbound"])

    @router.post("/systems/{serial}/status")
    async def post_telemetry(serial: str, request: Request) -> Response:
        body = await request.body()
        snapshot = parse_telemetry(_unwrap_form(body))
        await store.apply_telemetry(serial, snapshot)
        return Response(content=DIRECTIVE_XML, media_type="application/xml")

    @router.get("/Alive")
    async def heartbeat() -> Response:
        return Response(content=b"alive", media_type="text/plain")

    return router
