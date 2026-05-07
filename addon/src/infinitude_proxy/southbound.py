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
import re
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


# Match Perl `infinitude:597-601`: when we replay Carrier's directive
# verbatim to the thermostat, force `pingRate` to the clean cadence
# regardless of what Carrier returned. Carrier sometimes returns its
# own pingRate hint (e.g. 30 s during planned-server-maintenance) that
# we don't want governing local writes — the thermostat would then
# re-poll us 2.5x slower than our own dirty-flag dictates.
_PING_RATE_RE = re.compile(rb"<pingRate>\s*\d+\s*</pingRate>")


def _override_ping_rate(body: bytes, rate: int) -> bytes:
    return _PING_RATE_RE.sub(
        f"<pingRate>{rate}</pingRate>".encode("ascii"),
        body, count=1,
    )


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
        # Combine local-mutation flag and the post-Carrier-config
        # scheduled flag into one "any changes pending" decision —
        # mirrors Perl `infinitude:589` where `changes` can be either
        # 'true' or a future timestamp that becomes true when reached.
        local_changes = await store.take_config_dirty()
        scheduled_due = (
            bridge.consume_scheduled_changes() if bridge is not None else False
        )
        has_changes = local_changes or scheduled_due
        # Mirror status post to Carrier when the bridge is enabled
        # AND no local changes pending — Perl `infinitude:266`. Local
        # changes mean our directive says configHasChanges=true; the
        # thermostat will pull our local tree, and Carrier's stale
        # view shouldn't race that.
        relayed: CachedRelay | None = None
        if bridge is not None:
            relayed = await bridge.relay(
                "POST",
                f"/systems/{serial}/status",
                query=str(request.url.query) or None,
                headers=dict(request.headers),
                body=body,
                local_changes_pending=has_changes,
            )
        # Directive selection — Perl `infinitude:597-601`:
        #   - Local changes pending: send our local directive with
        #     configHasChanges=true. Carrier's response is ignored
        #     for this cycle (we already skipped the relay anyway).
        #   - Otherwise, if Carrier responded with a directive body,
        #     replay it to the thermostat with pingRate forced to
        #     the clean cadence. This is the path that propagates
        #     Carrier's `serverHasChanges=true` to the thermostat so
        #     it actually fetches config (without this, the
        #     `carrier_changes` window would expire unused after
        #     120 s).
        #   - Else build our local directive normally.
        if has_changes:
            content = _directive_xml(True)
        elif relayed is not None and relayed.status_code == 200 and relayed.body:
            content = _override_ping_rate(relayed.body, DIRECTIVE_PING_RATE_CLEAN)
        else:
            content = _directive_xml(False)
        return Response(content=content, media_type="application/xml")

    async def _bridge_mirror(method: str, path: str, request: Request, body: bytes | None = None) -> CachedRelay | None:
        """Fire-and-forget mirror to Carrier — used by routes whose
        local response shape we own (we ignore Carrier's response
        body but still want Carrier to see the same traffic the
        thermostat sends). Returns None when the bridge is disabled
        or the relay fails. Local-changes flag is read non-
        destructively here: these routes don't dictate the directive,
        so they shouldn't consume the dirty bit."""
        if bridge is None:
            return None
        return await bridge.relay(
            method, path,
            query=str(request.url.query) or None,
            headers=dict(request.headers),
            body=body,
            local_changes_pending=store.config_dirty,
        )

    async def _bridge_relay_or_local(
        method: str, path: str, request: Request,
        local_body: bytes, local_media_type: str = "application/xml",
    ) -> Response:
        """Relay to Carrier; if Carrier returned a body we use it,
        else fall through to a local stub. The release-notes /
        manifest / utility-events stubs all use this — Carrier may
        actually have content for any of them, and our local stub
        is just to keep the thermostat from retry-storming."""
        relayed = await _bridge_mirror(method, path, request, body=None)
        if relayed is not None and relayed.status_code == 200 and relayed.body:
            return Response(
                content=relayed.body,
                media_type=relayed.content_type or local_media_type,
            )
        return Response(content=local_body, media_type=local_media_type)

    @router.post("/systems/{serial}")
    async def post_system_config(serial: str, request: Request) -> Response:
        body = await request.body()
        tree, config = parse_system_config_with_tree(_unwrap_form(body))
        await store.apply_config(serial, config, tree)
        # Mirror boot/sync POST to Carrier unconditionally —
        # `local_changes_pending=False` here, NOT `store.config_dirty`.
        #
        # Why force False: the alpha.10 "skip relay when local changes
        # pending" rule exists to stop us from leaking in-flight HA
        # state to Carrier on *outbound* polls (status post, etc.).
        # That logic doesn't apply to a thermostat-originated
        # `POST /systems/{serial}`: the thermostat is *pushing* its
        # current view here (post-panel-change or post-boot), and
        # this body IS the device's authoritative state. Skipping the
        # mirror because HA happens to also have a pending write
        # would silently drop the only natural propagation channel
        # for panel-side changes — verified live alpha.46 (capture
        # showed two panel POSTs, one mirrored, one skipped because
        # apply_config's replay had set config_dirty).
        #
        # Perl `infinitude:259` likewise relays unconditionally on
        # boot POST (`!$store->get('changes')` is checked in
        # `before_dispatch`, but the boot-style POST hits that hook
        # before the local store's dirty bit can interfere).
        if bridge is not None:
            await bridge.relay(
                "POST", f"/systems/{serial}",
                query=str(request.url.query) or None,
                headers=dict(request.headers),
                body=body,
                local_changes_pending=False,
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
        to /systems/{serial} has populated the store; serial is
        currently not cross-checked against the store entry (single-
        unit deployment assumption, documented in DESIGN.md).

        Pull-observed clear: when the thermostat pulls config, any
        writes queued against this serial are assumed landed and are
        marked applied. Not a true confirmation (that would require
        matching the pulled tree against each pending mutation's
        expected value) but close enough — the thermostat only pulls
        after we signal configHasChanges, and it won't pull without
        then saving the payload.

        Carrier-changes pass-through: when the bridge has a fresh
        Carrier response cached AND its carrier_changes window is
        open (Carrier reported `serverHasChanges=true` recently in a
        relayed status POST), we serve Carrier's tree instead of
        ours — that tree carries the queued MyInfinity-app commands.
        Mirrors Perl `infinitude:567`. The window closes on first
        use so we don't keep returning the same response.
        """
        if bridge is not None and bridge.carrier_changes_active():
            cached = bridge.get_cached(f"GET /systems/{serial}/config")
            # Try to fetch a fresh Carrier config too — when the app
            # has queued changes, we want them, not the stale cache.
            # Forward the thermostat's auth headers (and querystring) —
            # without them Carrier replies 401 "consumer not found" and
            # we silently fall through to the local cached tree, which
            # is what masked the MyInfinity-app hold propagation bug.
            relayed = await bridge.relay(
                "GET", f"/systems/{serial}/config",
                query=str(request.url.query) or None,
                headers=dict(request.headers),
                local_changes_pending=False,
            )
            response = relayed or cached
            if response is not None and response.status_code == 200 and response.body:
                bridge.close_carrier_changes_window()
                # Persist Carrier's tree as our local store. Without
                # this the +60s re-sync below (and any northbound
                # write that flips config_dirty) would serve our
                # *stale* tree on the next /config GET, reverting
                # whatever Carrier just queued — exactly the
                # alpha.40 oscillation user saw: hold appears
                # (Carrier tree applied), 60s later hold reverts
                # (local stale tree applied), repeat.
                #
                # apply_config also runs REPLAY_REGISTRY on any
                # pending_writes, mutating `tree` in place. We then
                # serve the merged tree (Carrier's queued commands +
                # our pending HA-side writes) so the thermostat sees
                # both. Without merging here, an HA-side cancel-hold
                # issued while a Carrier-app hold was queued would be
                # silently reverted: the device receives Carrier's
                # raw tree (hold-on), local store reflects the merged
                # tree (hold-off), telemetry then re-confirms hold-on
                # and the cancel-hold "bounces back" — alpha.42 user
                # report.
                served_body = response.body
                served_ctype = response.content_type or "application/xml"
                try:
                    tree, config = parse_system_config_with_tree(response.body)
                    await store.apply_config(serial, config, tree)
                    merged = store.get_config()
                    if merged is not None:
                        served_body = serialize_config_tree(merged.tree)
                        served_ctype = "application/xml"
                    logger.info(
                        "carrier_bridge: synced local store from Carrier tree "
                        "(serial=%s, in=%d B, out=%d B)",
                        serial, len(response.body), len(served_body),
                    )
                except Exception as e:
                    # Don't block serving Carrier's tree on parse failure —
                    # the thermostat applies it either way. Log so the
                    # operator can tell why local store may be stale.
                    logger.warning(
                        "carrier_bridge: failed to parse Carrier tree for local "
                        "store sync (serial=%s): %s — serving body anyway",
                        serial, e,
                    )
                # Mark pending writes applied: the thermostat is about
                # to receive the merged tree, mirroring the non-bridge
                # serve path's mark_all_applied. Skipping this would
                # keep replaying the same writes onto every subsequent
                # carrier_changes serve.
                if store.persistence is not None:
                    applied_ids = await store.persistence.mark_all_applied(serial)
                    if applied_ids:
                        logger.info(
                            "persistence: marked %d pending write(s) applied "
                            "on carrier-bridge config serve serial=%s",
                            len(applied_ids), serial,
                        )
                # Schedule a forced config-fetch ~60 s out so the
                # thermostat re-syncs after applying the merged tree —
                # mirrors Perl `infinitude:572`.
                bridge.schedule_changes(60)
                logger.info(
                    "carrier_bridge: serving merged config to thermostat "
                    "(window consumed, scheduled changes 60s)"
                )
                return Response(
                    content=served_body,
                    media_type=served_ctype,
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
        await _bridge_mirror(
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
        await _bridge_mirror(
            "POST", f"/systems/{serial}/idu_config", request, body=body,
        )
        return Response(status_code=200)

    @router.post("/systems/{serial}/odu_config")
    async def post_odu_config(serial: str, request: Request) -> Response:
        body = await request.body()
        raw = _unwrap_form(body)
        config = parse_odu_config(raw)
        await store.apply_odu(serial, config, raw_xml=raw)
        await _bridge_mirror(
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
        await _bridge_mirror(
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
        `GET /v1/system/odu_status`."""
        body = await request.body()
        status = parse_odu_status(_unwrap_form(body))
        await store.apply_odu_status(serial, status)
        await _bridge_mirror(
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
        `GET /v1/system/idu_status`."""
        body = await request.body()
        status = parse_idu_status(_unwrap_form(body))
        await store.apply_idu_status(serial, status)
        await _bridge_mirror(
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
        await _bridge_mirror(
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
        await _bridge_mirror(
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
