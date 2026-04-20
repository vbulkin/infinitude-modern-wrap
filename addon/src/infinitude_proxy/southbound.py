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

import logging
from urllib.parse import unquote_to_bytes

from fastapi import APIRouter, Request, Response

from .parser import parse_notifications, parse_system_config, parse_telemetry
from .state_store import StateStore

logger = logging.getLogger(__name__)

DIRECTIVE_PING_RATE = 12

# TODO: metadata POSTs we currently accept-and-discard. Each one carries
# data we may eventually surface northbound; logging hits at INFO lets us
# confirm what a given thermostat actually sends before investing in a
# parser. Known subpaths observed in live captures:
#   profile          — hardware/firmware identity
#   dealer           — dealer contact record
#   idu_config       — indoor-unit capability map
#   odu_config       — outdoor-unit capability map
#   utility_events   — utility-rate / demand-response schedule


def _directive_xml(config_has_changes: bool) -> bytes:
    """Build the directive-channel response.

    Three fields; the only one that varies today is configHasChanges.
    True tells the thermostat to come back for a fresh /systems/{serial}
    dump; the ensuing POST clears the flag. pingRate is the telemetry
    poll cadence hint; Carrier's own server returned 12 in our captures
    regardless of dirty state, so we match that for now.
    """
    flag = b"true" if config_has_changes else b"false"
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<status version="1.37">'
        b'<configHasChanges>' + flag + b'</configHasChanges>'
        b'<pingRate>' + str(DIRECTIVE_PING_RATE).encode() + b'</pingRate>'
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
        return Response(
            content=_directive_xml(store.config_dirty),
            media_type="application/xml",
        )

    @router.post("/systems/{serial}")
    async def post_system_config(serial: str, request: Request) -> Response:
        body = await request.body()
        config = parse_system_config(_unwrap_form(body))
        await store.apply_config(serial, config)
        return Response(status_code=200)

    @router.post("/systems/{serial}/notifications")
    async def post_notifications(serial: str, request: Request) -> Response:
        body = await request.body()
        events = parse_notifications(_unwrap_form(body))
        await store.append_notifications(serial, events)
        return Response(status_code=200)

    # Metadata POSTs the thermostat also sends during boot (profile,
    # dealer, idu_config, odu_config, utility_events). Not consumed
    # yet — accept and discard so the thermostat doesn't retry. Log
    # each hit so we can audit which subpaths a given unit emits and
    # prioritize parser work. See the TODO block at top of this module.
    @router.post("/systems/{serial}/{subpath:path}")
    async def post_metadata_fallback(
        serial: str, subpath: str, request: Request
    ) -> Response:
        body = await request.body()
        logger.info(
            "unhandled thermostat POST serial=%s subpath=%s bytes=%d",
            serial, subpath, len(body),
        )
        return Response(status_code=200)

    @router.get("/Alive")
    async def heartbeat() -> Response:
        return Response(content=b"alive", media_type="text/plain")

    return router
