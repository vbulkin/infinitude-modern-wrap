"""Northbound mutation primitives — edit the retained `<config>` tree.

Each mutation is a small pure(ish) function (tree, payload) → None that
edits the lxml tree in place. The REPLAY_REGISTRY maps a string `kind`
to the function; the state store uses it both to apply the initial
mutation and to re-apply persisted PendingWrite rows onto a fresh tree
the thermostat posts back (the replay dispatcher that closes the
thermostat-reboot race from DESIGN.md §11.3).

Conventions:
  - Functions raise ValueError for "tree doesn't match payload" conditions
    (missing zone, malformed XML). The HTTP layer translates these to 404/422.
  - Payloads are the JSON-serializable dicts stored in `pending_writes.payload_json`.
    Keep them flat and descriptive — they're forensic artifacts if a replay
    ever has to be hand-inspected.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from lxml import etree

# ── Time helpers ─────────────────────────────────────────────────────

def snap_quarter_hour(hhmm: str) -> str:
    """Round an HH:MM string to the nearest quarter hour (00/15/30/45).

    Wraps at midnight so 23:53 → 00:00 rather than 24:00 (the thermostat
    rejects 24:xx). Matches the legacy UI's `durationToOtmr` rounding
    policy (round-half-up by minute). Empty input is returned unchanged —
    the thermostat treats an empty `<otmr/>` as "hold forever".
    """
    if not hhmm:
        return hhmm
    hh, mm = int(hhmm[:2]), int(hhmm[3:5])
    total = hh * 60 + mm
    total = ((total + 7) // 15) * 15
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def datetime_to_wall_time(dt: datetime) -> str:
    """Project an ISO datetime to HH:MM in the server's local wall time.

    The thermostat has no concept of timezone — its `<otmr>` is a bare
    HH:MM that it compares against its own local clock. We render into
    the server's local zone (Home Assistant sets this correctly on the
    host) and quarter-hour-snap. Naive datetimes are assumed UTC for
    forward-safety against JSON parsers that drop the tzinfo.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone()
    return snap_quarter_hour(f"{local.hour:02d}:{local.minute:02d}")


# ── Tree-edit helpers ────────────────────────────────────────────────

def _find_zone(tree: etree._Element, zone_id: str) -> etree._Element:
    """Locate <zones>/<zone id="N"> under the given config element."""
    zones = tree.find("zones")
    if zones is None:
        raise ValueError("config is missing <zones>")
    for z in zones.findall("zone"):
        if z.get("id") == zone_id:
            return z
    raise ValueError(f"zone {zone_id} not found")


def _set_or_create(parent: etree._Element, tag: str, text: str) -> None:
    """Set the text of <tag> under parent, inserting the child if absent.

    Preserves child ordering for existing elements — we only append when
    the tag wasn't there, which shouldn't happen for standard thermostat
    configs but guards against partial captures in tests.
    """
    el = parent.find(tag)
    if el is None:
        el = etree.SubElement(parent, tag)
    el.text = text


# ── Zone hold ────────────────────────────────────────────────────────

def apply_zone_hold_set(tree: etree._Element, payload: dict) -> None:
    """Enable a hold on a single zone.

    Payload shape:
      {"zone_id": "1", "activity": "manual", "otmr": "14:45"}
    An empty-string `otmr` means hold indefinitely (thermostat semantic).
    """
    zone = _find_zone(tree, payload["zone_id"])
    _set_or_create(zone, "hold", "on")
    _set_or_create(zone, "holdActivity", payload["activity"])
    _set_or_create(zone, "otmr", payload.get("otmr", ""))


def apply_zone_hold_clear(tree: etree._Element, payload: dict) -> None:
    """Release a zone hold — `<hold>off</hold>`, clear activity + otmr.

    The thermostat reads `holdActivity=none` as "no hold currently
    selected", mirroring what the boot fixture shows for unheld zones.
    Clearing `<otmr>` keeps the element present but empty so the wire
    shape doesn't change.
    """
    zone = _find_zone(tree, payload["zone_id"])
    _set_or_create(zone, "hold", "off")
    _set_or_create(zone, "holdActivity", "none")
    _set_or_create(zone, "otmr", "")


# ── Replay dispatcher registry ───────────────────────────────────────

MutationFn = Callable[[etree._Element, dict], None]

REPLAY_REGISTRY: dict[str, MutationFn] = {
    "zone_hold_set": apply_zone_hold_set,
    "zone_hold_clear": apply_zone_hold_clear,
}
