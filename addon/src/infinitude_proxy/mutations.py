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

    Empty-string `text` is stored as None so lxml serializes the element
    self-closing (`<tag/>`) rather than with an empty content pair
    (`<tag></tag>`). The thermostat's XML parser is strict about this —
    live captures always use self-closing for optional fields (otmr on an
    unheld zone, holdActivity on an unheld zone), and feeding it the
    empty-content shape causes silent rejection of the config pull.
    """
    el = parent.find(tag)
    if el is None:
        el = etree.SubElement(parent, tag)
    el.text = text if text else None


# ── Zone manual setpoints (composite: activity edit + hold) ──────────

def _find_activity(zone: etree._Element, activity_id: str) -> etree._Element:
    acts = zone.find("activities")
    if acts is None:
        raise ValueError("zone is missing <activities>")
    for a in acts.findall("activity"):
        if a.get("id") == activity_id:
            return a
    raise ValueError(f"activity {activity_id} not found in zone {zone.get('id')}")


def _format_setpoint(value: int) -> str:
    """Render an integer setpoint as the thermostat's `NN.0` convention.

    Captured configs use a single decimal place ("68.0"). Writing the
    bare integer would round-trip fine through our parser but drifts
    from what the thermostat emits — keep the wire format stable so
    diffs against golden captures stay clean.
    """
    return f"{value}.0"


def apply_zone_setpoints_set(tree: etree._Element, payload: dict) -> None:
    """Update a zone's `manual` activity setpoints and (by default) engage
    the manual hold.

    Payload shape:
      {"zone_id": "1", "heat": 68, "cool": 76, "activate_hold": True}
    Either or both of heat/cool may be omitted — the mutation only writes
    the fields present in the payload, so a PATCH with just `cool` leaves
    `htsp` alone. When `activate_hold` is true (the default in the API
    surface), we also flip hold=on/holdActivity=manual/otmr=empty so the
    new setpoints take effect immediately; without it, the setpoints are
    staged for the next time the user manually activates the hold.
    """
    zone = _find_zone(tree, payload["zone_id"])
    manual = _find_activity(zone, "manual")
    if "heat" in payload and payload["heat"] is not None:
        _set_or_create(manual, "htsp", _format_setpoint(int(payload["heat"])))
    if "cool" in payload and payload["cool"] is not None:
        _set_or_create(manual, "clsp", _format_setpoint(int(payload["cool"])))
    if payload.get("activate_hold", True):
        _set_or_create(zone, "hold", "on")
        _set_or_create(zone, "holdActivity", "manual")
        _set_or_create(zone, "otmr", "")


# ── Activity edit ────────────────────────────────────────────────────

def apply_activity_set(tree: etree._Element, payload: dict) -> None:
    """Edit one activity's setpoints and/or fan — sparse update.

    Payload shape:
      {"zone_id": "1", "activity_id": "home", "heat": 68, "cool": 74, "fan": "low"}
    Any of heat/cool/fan may be omitted; only supplied keys touch the tree.
    Unlike apply_zone_setpoints_set (which is the hold-engaging "manual"
    composite), this mutation does not touch hold state — editing the
    `home` activity's setpoints shouldn't silently engage a hold. If the
    zone is already holding on this activity the change takes effect at
    the next thermostat refresh; otherwise it's staged for the next time
    the activity runs.
    """
    zone = _find_zone(tree, payload["zone_id"])
    activity = _find_activity(zone, payload["activity_id"])
    if "heat" in payload and payload["heat"] is not None:
        _set_or_create(activity, "htsp", _format_setpoint(int(payload["heat"])))
    if "cool" in payload and payload["cool"] is not None:
        _set_or_create(activity, "clsp", _format_setpoint(int(payload["cool"])))
    if "fan" in payload and payload["fan"] is not None:
        _set_or_create(activity, "fan", str(payload["fan"]))


# ── Schedule (7-day program overwrite) ───────────────────────────────

def apply_schedule_set(tree: etree._Element, payload: dict) -> None:
    """Overwrite a zone's 7-day schedule.

    Payload shape:
      {
        "zone_id": "1",
        "days": [
          {"day": "Sunday", "periods": [
            {"id": 1, "activity": "wake", "time": "06:00", "enabled": true},
            ...
          ]},
          ... (all seven days)
        ]
      }

    Strategy: rebuild the `<program>` subtree from scratch rather than
    diff. Schedule writes are coarse-grained (whole program replaced),
    and the wire shape is compact enough that round-tripping seven days
    × up to five periods is cheap. Absent `<program>` (partial fixtures)
    gets created.
    """
    zone = _find_zone(tree, payload["zone_id"])
    prog = zone.find("program")
    if prog is None:
        prog = etree.SubElement(zone, "program")
    for d in list(prog.findall("day")):
        prog.remove(d)
    for day in payload["days"]:
        day_el = etree.SubElement(prog, "day")
        day_el.set("id", day["day"])
        for period in day["periods"]:
            period_el = etree.SubElement(day_el, "period")
            period_el.set("id", str(period["id"]))
            act_el = etree.SubElement(period_el, "activity")
            act_el.text = str(period["activity"])
            time_el = etree.SubElement(period_el, "time")
            time_el.text = period["time"]
            enabled_el = etree.SubElement(period_el, "enabled")
            enabled_el.text = "on" if period["enabled"] else "off"


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

    Wire shape for an unheld zone is `<holdActivity/>` (empty self-
    closing) and `<otmr/>`, per live captures. The whole-house hold
    uses `<holdActivity>none</holdActivity>` for the cleared state, but
    at zone level the literal "none" is not a valid ActivityId and the
    thermostat silently rejects the whole config pull when we send it.
    `_set_or_create` with empty text writes self-closing, matching what
    the thermostat emits when the wall panel releases a hold.
    """
    zone = _find_zone(tree, payload["zone_id"])
    _set_or_create(zone, "hold", "off")
    _set_or_create(zone, "holdActivity", "")
    _set_or_create(zone, "otmr", "")


# ── System mode ──────────────────────────────────────────────────────

def apply_system_mode_set(tree: etree._Element, payload: dict) -> None:
    """Set the HVAC mode — `<mode>off|heat|cool|auto|fanonly</mode>`.

    Payload shape: {"mode": "heat"}. The mode element lives at the top
    of <config> (sibling to <zones>/<wholeHouse>) and always exists in
    captured configs; we use _set_or_create defensively for partial
    fixtures. Validity of the enum value is enforced by pydantic at the
    HTTP boundary (HvacMode).
    """
    _set_or_create(tree, "mode", payload["mode"])


# ── Vacation ─────────────────────────────────────────────────────────

def _iso_for_vacation(dt: datetime) -> str:
    """Render a datetime in the ISO format the thermostat expects.

    Observed configs use `YYYY-MM-DDTHH:MM:SS` (no tz suffix); Python's
    isoformat is compatible when we strip the microseconds. Naive
    datetimes are assumed UTC (same convention as datetime_to_wall_time)
    but we strip tz before serializing because the thermostat's config
    tree is tz-naive — its own clock is local-wall time.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt.replace(microsecond=0).isoformat()


def apply_vacation_set(tree: etree._Element, payload: dict) -> None:
    """Write vacation fields — sparse update, only supplied keys touch
    the tree.

    Payload keys (any subset):
      active: True|False   → <vacat>on|off</vacat>
      start: ISO datetime  → <vacstart>...</vacstart>
      end: ISO datetime    → <vacend>...</vacend>
      heatSetpoint: int    → <vacmint>NN.0</vacmint>
      coolSetpoint: int    → <vacmaxt>NN.0</vacmaxt>
      fan: FanSpeed str    → <vacfan>...</vacfan>

    Clearing dates is deliberately not supported — to exit vacation,
    set active=False. Thermostat behavior: disabling leaves the window
    in place for "next time"; clearing it requires a rewrite of both
    dates anyway, so keeping the cleared-value contract out of this
    sparse surface keeps the payload unambiguous.
    """
    if "active" in payload and payload["active"] is not None:
        _set_or_create(tree, "vacat", "on" if payload["active"] else "off")
    if "start" in payload and payload["start"] is not None:
        start = payload["start"]
        if isinstance(start, str):
            start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        _set_or_create(tree, "vacstart", _iso_for_vacation(start))
    if "end" in payload and payload["end"] is not None:
        end = payload["end"]
        if isinstance(end, str):
            end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        _set_or_create(tree, "vacend", _iso_for_vacation(end))
    if "heatSetpoint" in payload and payload["heatSetpoint"] is not None:
        _set_or_create(tree, "vacmint", _format_setpoint(int(payload["heatSetpoint"])))
    if "coolSetpoint" in payload and payload["coolSetpoint"] is not None:
        _set_or_create(tree, "vacmaxt", _format_setpoint(int(payload["coolSetpoint"])))
    if "fan" in payload and payload["fan"] is not None:
        _set_or_create(tree, "vacfan", str(payload["fan"]))


# ── Humidity targets ─────────────────────────────────────────────────

def apply_humidity_set(tree: etree._Element, payload: dict) -> None:
    """Write per-mode humidity targets — sparse update, only supplied
    keys are written.

    Payload shape (any subset):
      {"targetHome": 40, "targetAway": 35, "targetVacation": 30}
    Each value is an integer 0–100. Targets live as flat children of
    <config> named `humidityHome`/`humidityAway`/`humidityVacation` —
    siblings of `<cfghumid>`, not nested. Pydantic's PercentInt bounds
    enforce the 0–100 range at the HTTP boundary.
    """
    for key, tag in (
        ("targetHome", "humidityHome"),
        ("targetAway", "humidityAway"),
        ("targetVacation", "humidityVacation"),
    ):
        if key in payload and payload[key] is not None:
            _set_or_create(tree, tag, str(int(payload[key])))


# ── Whole-house (system) hold ────────────────────────────────────────

def _find_whole_house(tree: etree._Element) -> etree._Element:
    wh = tree.find("wholeHouse")
    if wh is None:
        raise ValueError("config is missing <wholeHouse>")
    return wh


def apply_system_hold_set(tree: etree._Element, payload: dict) -> None:
    """Enable the whole-house hold.

    Payload shape:
      {"activity": "home", "otmr": "14:45"}
    SystemHoldActivity is narrower than ActivityId — only home/away/
    sleep/wake are valid at the whole-house level (no "manual"); we
    rely on pydantic at the HTTP boundary to enforce that.
    """
    wh = _find_whole_house(tree)
    _set_or_create(wh, "hold", "on")
    _set_or_create(wh, "holdActivity", payload["activity"])
    _set_or_create(wh, "otmr", payload.get("otmr", ""))


def apply_system_hold_clear(tree: etree._Element, payload: dict) -> None:
    """Release the whole-house hold. Mirrors apply_zone_hold_clear —
    `<hold>off</hold>`, `<holdActivity>none</holdActivity>`, empty otmr."""
    wh = _find_whole_house(tree)
    _set_or_create(wh, "hold", "off")
    _set_or_create(wh, "holdActivity", "none")
    _set_or_create(wh, "otmr", "")


# ── Replay dispatcher registry ───────────────────────────────────────

MutationFn = Callable[[etree._Element, dict], None]

REPLAY_REGISTRY: dict[str, MutationFn] = {
    "zone_hold_set": apply_zone_hold_set,
    "zone_hold_clear": apply_zone_hold_clear,
    "system_hold_set": apply_system_hold_set,
    "system_hold_clear": apply_system_hold_clear,
    "system_mode_set": apply_system_mode_set,
    "zone_setpoints_set": apply_zone_setpoints_set,
    "activity_set": apply_activity_set,
    "schedule_set": apply_schedule_set,
    "humidity_set": apply_humidity_set,
    "vacation_set": apply_vacation_set,
}
