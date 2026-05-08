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

import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import unquote_to_bytes

from fastapi import APIRouter, Request, Response

from .carrier_bridge import CachedRelay, CarrierBridge
from .parser import (
    parse_energy,
    parse_equipment_events,
    parse_idu_config,
    parse_idu_status,
    parse_notifications,
    parse_odu_config,
    parse_odu_status,
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


def create_southbound_router(
    store: StateStore,
    bridge: CarrierBridge | None = None,
) -> APIRouter:
    router = APIRouter(tags=["southbound"])

    @router.post("/systems/{serial}/status")
    async def post_telemetry(serial: str, request: Request) -> Response:
        body = await request.body()
        snapshot = parse_telemetry(_unwrap_form(body))
        await store.apply_telemetry(serial, snapshot)
        local_changes = await store.take_config_dirty()
        # Mirror status post to Carrier (every tick — Carrier's pingRate
        # directive handles device-side rate limiting natively). Skip
        # only when HA has a write queued: the thermostat will pull our
        # local tree next, and Carrier's stale view shouldn't race that.
        # Otherwise we relay so Carrier's view of telemetry stays current
        # and we observe `serverHasChanges=true` the moment Carrier flips
        # it.
        relayed: CachedRelay | None = None
        if bridge is not None:
            relayed = await bridge.relay(
                "POST",
                f"/systems/{serial}/status",
                query=str(request.url.query) or None,
                headers=dict(request.headers),
                body=body,
                local_changes_pending=local_changes,
            )
        # Carrier signalled `serverHasChanges=true` → the MyInfinity app
        # queued a config change. We can't pull from Carrier ourselves
        # (no auth: Carrier OAuth requires single-use nonces signed by
        # firmware-resident secrets — see carrier_bridge module
        # docstring). Instead we latch the signal: the thermostat's next
        # /config GET goes through the cold-start fallback in
        # `get_system_config`, which relays the GET to Carrier using the
        # thermostat's own auth headers and merges the result.
        if (
            bridge is not None
            and not local_changes
            and relayed is not None
            and relayed.status_code == 200
            and bridge.has_server_changes(relayed.body)
        ):
            bridge.signal_carrier_has_changes()
        # Directive selection:
        #   - Local changes pending: send configHasChanges=true with
        #     our DIRTY pingRate so the thermostat re-polls fast and
        #     picks up our local tree.
        #   - Otherwise, if Carrier responded with a directive body,
        #     forward it VERBATIM (including Carrier's pingRate).
        #     Pre-alpha.48 we stripped Carrier's pingRate and forced
        #     12 s — that defeated Carrier's authoritative rate-limit
        #     signal. Carrier's pingRate is now respected end-to-end
        #     in clean state; only DIRTY state overrides.
        #   - Else build our local directive normally (CLEAN cadence).
        if local_changes:
            content = _directive_xml(True)
        elif relayed is not None and relayed.status_code == 200 and relayed.body:
            content = relayed.body
        else:
            content = _directive_xml(False)
        return Response(content=content, media_type="application/xml")

    def _bridge_mirror_fire_and_forget(
        method: str, path: str, request: Request, body: bytes | None = None,
    ) -> None:
        """Fire-and-forget mirror to Carrier for routes whose local
        response shape we own (we ignore Carrier's response body but
        still want Carrier to see the same traffic the thermostat
        sends). Used by notifications, idu_config, odu_config,
        equipment_events, energy, boot POST.

        Why fire-and-forget: these routes don't depend on Carrier's
        response, but pre-alpha.48 the relay was synchronously
        awaited — so a slow or unreachable Carrier would make the
        thermostat wait up to 10 s per call. With the change, the
        thermostat replies in the local response time (<10 ms) and
        the upstream mirror runs on the event loop in the background.
        Errors inside the relay are caught + logged; a discarded task
        can't surface an unhandled exception.

        local_changes_pending=False because these are thermostat-
        originated POSTs — the body IS the device's authoritative
        state, NOT a poll where HA-side dirty bit could race. (See
        the alpha.46 panel-mirror-skip side bug fix for context.)
        """
        if bridge is None:
            return
        asyncio.create_task(
            bridge.relay(
                method, path,
                query=str(request.url.query) or None,
                headers=dict(request.headers),
                body=body,
                local_changes_pending=False,
            ),
            name=f"carrier_mirror_{method}_{path}",
        )

    async def _bridge_relay_or_local(
        method: str, path: str, request: Request,
        local_body: bytes, local_media_type: str = "application/xml",
    ) -> Response:
        """Relay to Carrier; if Carrier returned a body we use it,
        else fall through to a local stub. The release-notes /
        manifest / utility-events stubs all use this — Carrier may
        actually have content for any of them, and our local stub
        is just to keep the thermostat from retry-storming.

        Synchronous because the response body is what we serve back
        to the thermostat. Bounded by `CarrierBridge._timeout` (3 s
        in alpha.48) so a slow Carrier can't make the thermostat hang.
        """
        if bridge is None:
            return Response(content=local_body, media_type=local_media_type)
        relayed = await bridge.relay(
            method, path,
            query=str(request.url.query) or None,
            headers=dict(request.headers),
            body=None,
            local_changes_pending=False,
        )
        if relayed is not None and relayed.status_code == 200 and relayed.body:
            return Response(
                content=relayed.body,
                media_type=relayed.content_type or local_media_type,
            )
        return Response(content=local_body, media_type=local_media_type)

    @router.post("/systems/{serial}")
    async def post_system_config(serial: str, request: Request) -> Response:
        """Boot/sync POST from the thermostat — full config tree.

        Mirror is fire-and-forget as of alpha.48: this body IS the
        device's authoritative state, and we don't read Carrier's
        response back, so awaiting it just makes the thermostat wait
        on Carrier's latency for no functional gain.

        `local_changes_pending=False` is correct here, NOT
        `store.config_dirty` — the thermostat is *pushing* its
        current view, not polling. Skipping the mirror because HA
        happens to also have a pending write would silently drop the
        only natural panel-change propagation channel (verified live
        alpha.46 capture: panel POST #2 silently skipped because
        apply_config's replay had set config_dirty).
        """
        body = await request.body()
        tree, config = parse_system_config_with_tree(_unwrap_form(body))
        await store.apply_config(serial, config, tree)
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}", request, body=body,
        )
        return Response(status_code=200)

    @router.get("/systems/{serial}/config")
    async def get_system_config(serial: str, request: Request) -> Response:
        """Serve the retained <config> subtree to the thermostat.

        The thermostat fetches this path after receiving a directive
        with configHasChanges=true. We serve the in-memory tree —
        which includes any northbound mutations — as
        `<?xml ...?>\\n<config>...</config>`, matching the live
        Mojolicious wire format. 404 until the thermostat's boot POST
        to /systems/{serial} has populated the store.

        Pull-observed clear: when the thermostat pulls config, any
        writes queued against this serial are assumed landed and are
        marked applied. Not a true confirmation (that would require
        matching the pulled tree against each pending mutation's
        expected value) but close enough — the thermostat only pulls
        after we signal configHasChanges, and it won't pull without
        then saving the payload.

        Carrier-app pull-through: when Carrier signalled
        `serverHasChanges=true` on the previous status POST, the bridge
        latched a `pending_carrier_pull` flag. We can't pull on our own
        — Carrier OAuth uses single-use nonces signed by firmware-
        resident secrets, so the proxy has no way to mint a request
        Carrier will accept (see carrier_bridge module docstring). What
        we CAN do: piggy-back on this thermostat-originated /config GET,
        which carries auth Carrier accepts on this route, relay it
        upstream, and merge the response into the local tree before
        serving it back. This is the only path by which Carrier-app-
        originated changes reach HA.
        """
        if bridge is not None and bridge.take_pending_carrier_pull():
            relayed = await bridge.relay(
                "GET", f"/systems/{serial}/config",
                query=str(request.url.query) or None,
                headers=dict(request.headers),
                local_changes_pending=False,
            )
            if relayed is not None and relayed.status_code == 200 and relayed.body:
                try:
                    tree, config = parse_system_config_with_tree(relayed.body)
                    await store.apply_config(serial, config, tree)
                    logger.info(
                        "carrier_bridge: pull-through applied "
                        "(serial=%s, %d B)", serial, len(relayed.body),
                    )
                except Exception as e:
                    logger.warning(
                        "carrier_bridge: pull-through parse failed "
                        "(serial=%s): %s — falling through to local tree",
                        serial, e,
                    )
            elif relayed is not None:
                logger.warning(
                    "carrier_bridge: pull-through non-200 from Carrier "
                    "(serial=%s, status=%d) — serving local tree",
                    serial, relayed.status_code,
                )

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
        # Mirror notifications to Carrier so the MyInfinity app can
        # surface alerts (filter due, fault codes, etc.).
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/notifications", request, body=body,
        )
        return Response(status_code=200)

    @router.post("/systems/{serial}/idu_config")
    async def post_idu_config(serial: str, request: Request) -> Response:
        body = await request.body()
        raw = _unwrap_form(body)
        config = parse_idu_config(raw)
        await store.apply_idu(serial, config, raw_xml=raw)
        # Mirror equipment descriptor — Carrier needs it to know what
        # hardware is talking (fancoil vs. furnace, etc.).
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/idu_config", request, body=body,
        )
        return Response(status_code=200)

    @router.post("/systems/{serial}/odu_config")
    async def post_odu_config(serial: str, request: Request) -> Response:
        body = await request.body()
        raw = _unwrap_form(body)
        config = parse_odu_config(raw)
        await store.apply_odu(serial, config, raw_xml=raw)
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/odu_config", request, body=body,
        )
        return Response(status_code=200)

    @router.post("/systems/{serial}/energy")
    async def post_energy(serial: str, request: Request) -> Response:
        """Per-mode runtime hours + efficiency ratings — feeds the
        MyInfinity app's energy dashboard. Posted ~daily by the
        thermostat. Surfaces northbound at `GET /v1/system/energy`."""
        body = await request.body()
        energy = parse_energy(_unwrap_form(body))
        await store.apply_energy(serial, energy)
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/energy", request, body=body,
        )
        logger.info(
            "energy: serial=%s seer=%s hspf=%s periods=%d",
            serial, energy.seer, energy.hspf, len(energy.usage),
        )
        return Response(status_code=200)

    @router.post("/systems/{serial}/odu_status")
    async def post_odu_status(serial: str, request: Request) -> Response:
        """Outdoor-unit live runtime — compressor stage + RPM,
        refrigerant pressures, blower state. Surfaces northbound at
        `GET /v1/system/odu_status`. Raw XML is persisted (alpha.50)
        so HA stage/RPM/pressure sensors don't go `unavailable` for
        hours after an addon restart on an idle system."""
        body = await request.body()
        raw = _unwrap_form(body)
        status = parse_odu_status(raw)
        await store.apply_odu_status(serial, status, raw_xml=raw)
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/odu_status", request, body=body,
        )
        logger.info(
            "odu_status: serial=%s opstat=%r stage=%s opmode=%s oat=%s comprpm=%s",
            serial, status.opstat, status.operatingStage, status.opmode,
            status.outdoorTemperature, status.compressorRpm,
        )
        return Response(status_code=200)

    @router.post("/systems/{serial}/idu_status")
    async def post_idu_status(serial: str, request: Request) -> Response:
        """Indoor-unit live runtime — blower RPM, airflow CFM,
        static pressure, coil temp. Surfaces northbound at
        `GET /v1/system/idu_status`. Raw XML is persisted (alpha.50);
        same rationale as odu_status."""
        body = await request.body()
        raw = _unwrap_form(body)
        status = parse_idu_status(raw)
        await store.apply_idu_status(serial, status, raw_xml=raw)
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/idu_status", request, body=body,
        )
        logger.info(
            "idu_status: serial=%s opstat=%r stage=%s blwrpm=%s cfm=%s",
            serial, status.opstat, status.operatingStage,
            status.blowerRpm, status.iduCfm,
        )
        return Response(status_code=200)

    @router.post("/systems/{serial}/equipment_events")
    async def post_equipment_events(serial: str, request: Request) -> Response:
        """Thermostat fault history. POSTed when the unit observes a
        new fault or cycles its event list. Surfaces northbound at
        `GET /v1/system/events`."""
        body = await request.body()
        events = parse_equipment_events(_unwrap_form(body))
        await store.apply_equipment_events(serial, events)
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/equipment_events", request, body=body,
        )
        active = sum(1 for e in events.events if e.active)
        logger.info(
            "equipment_events: serial=%s total=%d active=%d",
            serial, len(events.events), active,
        )
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
        # Mirror unhandled metadata posts too — Carrier might use
        # them (utility_events, history, energy, etc.). Cheap to
        # forward; ignored locally.
        _bridge_mirror_fire_and_forget(
            "POST", f"/systems/{serial}/{subpath}", request, body=body,
        )
        return Response(status_code=200)

    @router.get("/Alive")
    async def heartbeat(request: Request) -> Response:
        return await _bridge_relay_or_local(
            "GET", "/Alive", request,
            local_body=b"alive", local_media_type="text/plain",
        )

    # Stubs for thermostat GETs we don't implement but silence to keep
    # logs clean. utility_events is a demand-response rate schedule the
    # device polls from Carrier's cloud; manifest is a firmware-update
    # check. Returning empty 200 bodies matches upstream Perl Infinitude
    # when offline; if the bridge is enabled we serve Carrier's actual
    # content when available.
    @router.get("/systems/{serial}/utility_events")
    async def get_utility_events(serial: str, request: Request) -> Response:
        return await _bridge_relay_or_local(
            "GET", f"/systems/{serial}/utility_events", request,
            local_body=b'<?xml version="1.0" encoding="UTF-8"?>\n<utility_events/>',
            local_media_type="application/xml",
        )

    @router.get("/manifest")
    async def get_manifest(request: Request) -> Response:
        return await _bridge_relay_or_local(
            "GET", "/manifest", request,
            local_body=b"", local_media_type="application/octet-stream",
        )

    # Firmware-release-notes probe. Thermostat polls
    # `/releaseNotes/{model}-{firmware}.txt` (e.g. systxbbec-14.02.txt)
    # directly at the proxy; a 404 triggers a tight retry loop, a 200
    # (even empty) quiets it. With the bridge enabled we relay to
    # Carrier which may serve real release notes; otherwise we return
    # an empty 200 to match upstream Perl Infinitude's offline mode.
    @router.get("/releaseNotes/{path:path}")
    async def get_release_notes(path: str, request: Request) -> Response:
        return await _bridge_relay_or_local(
            "GET", f"/releaseNotes/{path}", request,
            local_body=b"", local_media_type="text/plain",
        )

    return router
