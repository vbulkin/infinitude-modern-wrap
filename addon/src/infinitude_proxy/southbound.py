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
import os
from pathlib import Path
from urllib.parse import unquote_to_bytes

from fastapi import APIRouter, Request, Response

from .parser import (
    parse_idu_config,
    parse_notifications,
    parse_odu_config,
    parse_system_config_with_tree,
    parse_telemetry,
    serialize_config_tree,
)
from .state_store import StateStore

logger = logging.getLogger(__name__)

# Telemetry poll cadence hint (seconds) returned in the directive.
# Clean state: Carrier's own server returned 12 in our captures; we
# match that. Dirty state: captures show 20 — a shorter cadence so the
# thermostat picks up pending config changes faster. Values confirmed
# against upstream Perl Infinitude and the nb_api_session capture.
DIRECTIVE_PING_RATE_CLEAN = 12
DIRECTIVE_PING_RATE_DIRTY = 20

# TODO: metadata POSTs we currently accept-and-discard. Each one carries
# data we may eventually surface northbound. The fallback handler now
# dumps the first body seen per subpath so we have a real sample for
# parser work; subsequent hits just log byte count. Known subpaths
# observed in live captures:
#   profile          — hardware/firmware identity
#   dealer           — dealer contact record
#   utility_events   — utility-rate / demand-response schedule
#   history          — observed 2026-04-21, ~1118 bytes per POST
_METADATA_SAMPLE_DIR = Path(
    os.getenv("INFINITUDE_METADATA_SAMPLE_DIR", "metadata_samples")
)
_SEEN_SUBPATHS: set[str] = set()


def _capture_metadata_sample(subpath: str, raw: bytes) -> bool:
    """First-seen dedupe: write the unwrapped XML body on first
    encounter of a subpath so we have a payload sample to drive parser
    work, then skip on subsequent hits. Returns True if a sample was
    written this call. Write failures are non-fatal — we still 200 the
    thermostat so it doesn't retry.
    """
    if subpath in _SEEN_SUBPATHS:
        return False
    _SEEN_SUBPATHS.add(subpath)
    try:
        _METADATA_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
        safe = subpath.replace("/", "_") or "root"
        (_METADATA_SAMPLE_DIR / f"{safe}.xml").write_bytes(raw)
        return True
    except OSError as e:
        logger.warning(
            "metadata sample write failed subpath=%s err=%s", subpath, e
        )
        return False


def _directive_xml(config_has_changes: bool) -> bytes:
    """Build the directive-channel response.

    Two signals the thermostat acts on: configHasChanges tells it to
    GET /systems/{serial}/config (pull the mutated tree) and pingRate
    sets the telemetry cadence. Upstream Perl returns 20 while dirty
    and 12 otherwise — a shorter cadence so pending edits get picked
    up sooner. serverHasChanges stays false; we don't run the Carrier
    cloud's "server settings" side channel.
    """
    flag = b"true" if config_has_changes else b"false"
    ping = (
        DIRECTIVE_PING_RATE_DIRTY if config_has_changes else DIRECTIVE_PING_RATE_CLEAN
    )
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<status version="1.37">'
        b'<configHasChanges>' + flag + b'</configHasChanges>'
        b'<pingRate>' + str(ping).encode() + b'</pingRate>'
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
        # Atomic read-and-clear: if dirty, this response signals the
        # thermostat to re-pull config AND the flag is already false
        # for the next status POST. Matches upstream Perl's optimistic
        # clear — see StateStore.take_config_dirty().
        has_changes = await store.take_config_dirty()
        return Response(
            content=_directive_xml(has_changes),
            media_type="application/xml",
        )

    @router.post("/systems/{serial}")
    async def post_system_config(serial: str, request: Request) -> Response:
        body = await request.body()
        tree, config = parse_system_config_with_tree(_unwrap_form(body))
        await store.apply_config(serial, config, tree)
        return Response(status_code=200)

    @router.get("/systems/{serial}/config")
    async def get_system_config(serial: str) -> Response:
        """Serve the retained <config> subtree to the thermostat.

        The thermostat fetches this path after receiving a directive
        with configHasChanges=true. We serve the in-memory tree — which
        will include any northbound mutations once Slice 2 lands — as
        `<?xml ...?>\\n<config>...</config>`, matching the live
        Mojolicious wire format. 404 until the thermostat's boot POST
        to /systems/{serial} has populated the store; serial is
        currently not cross-checked against the store entry (single-
        unit deployment assumption, documented in DESIGN.md).

        Pull-observed clear: when the thermostat pulls config, any
        writes queued against this serial are assumed landed and are
        marked applied. Not a true confirmation (that would require
        matching the pulled tree against each pending mutation's
        expected value) but close enough for Slice 2 — the thermostat
        only pulls after we signal configHasChanges, and it won't pull
        without then saving the payload.
        """
        stored = store.get_config()
        if stored is None:
            return Response(status_code=404)
        if store.persistence is not None:
            applied_ids = await store.persistence.mark_all_applied(serial)
            if applied_ids:
                logger.info(
                    "persistence: marked %d pending write(s) applied on config pull serial=%s",
                    len(applied_ids), serial,
                )
        return Response(
            content=serialize_config_tree(stored.tree),
            media_type="application/xml",
        )

    @router.post("/systems/{serial}/notifications")
    async def post_notifications(serial: str, request: Request) -> Response:
        body = await request.body()
        events = parse_notifications(_unwrap_form(body))
        await store.append_notifications(serial, events)
        return Response(status_code=200)

    @router.post("/systems/{serial}/idu_config")
    async def post_idu_config(serial: str, request: Request) -> Response:
        body = await request.body()
        raw = _unwrap_form(body)
        config = parse_idu_config(raw)
        await store.apply_idu(serial, config, raw_xml=raw)
        return Response(status_code=200)

    @router.post("/systems/{serial}/odu_config")
    async def post_odu_config(serial: str, request: Request) -> Response:
        body = await request.body()
        raw = _unwrap_form(body)
        config = parse_odu_config(raw)
        await store.apply_odu(serial, config, raw_xml=raw)
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
        captured = _capture_metadata_sample(subpath, _unwrap_form(body))
        logger.info(
            "unhandled thermostat POST serial=%s subpath=%s bytes=%d%s",
            serial, subpath, len(body),
            " sample_captured" if captured else "",
        )
        return Response(status_code=200)

    @router.get("/Alive")
    async def heartbeat() -> Response:
        return Response(content=b"alive", media_type="text/plain")

    # Stubs for thermostat GETs we don't implement but silence to keep
    # logs clean. utility_events is a demand-response rate schedule the
    # device polls from Carrier's cloud; manifest is a firmware-update
    # check. Returning empty 200 bodies matches upstream Perl Infinitude.
    @router.get("/systems/{serial}/utility_events")
    async def get_utility_events(serial: str) -> Response:
        return Response(
            content=b'<?xml version="1.0" encoding="UTF-8"?>\n<utility_events/>',
            media_type="application/xml",
        )

    @router.get("/manifest")
    async def get_manifest() -> Response:
        return Response(content=b"", media_type="application/octet-stream")

    # Firmware-release-notes probe. Thermostat polls
    # `/releaseNotes/{model}-{firmware}.txt` (e.g. systxbbec-14.02.txt)
    # directly at the proxy; a 404 triggers a tight retry loop, a 200
    # (even empty) quiets it. Matches upstream Perl Infinitude. The
    # forward-proxy form (`/http%3A//www.ota.ing.carrier.com/releaseNotes/...`)
    # is a separate concern handled by the future Carrier passthrough.
    @router.get("/releaseNotes/{path:path}")
    async def get_release_notes(path: str) -> Response:
        return Response(content=b"", media_type="text/plain")

    return router
