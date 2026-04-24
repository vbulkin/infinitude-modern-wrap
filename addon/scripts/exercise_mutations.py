"""Walk through every /v1/* mutation kind with fixed pacing.

Two uses:
  1. Drive the capture table across all mutation kinds during a fixture
     harvest run — produces a clean, temporally-separated sequence in
     `_index.tsv` so curation is a matter of picking the N rows per
     kind rather than untangling interleaved traffic.
  2. Post-cutover smoke test: confirm each mutation shape is accepted
     by the proxy + echoed back through telemetry (no silent rejects,
     no drift).

Each mutation is paired with its reverse so the thermostat ends the
run in roughly the state it started in. Schedule_set is skipped by
default — it needs the full 7-day body and defaults that "restore
to original" would overwrite anything a user had customized; pass
`--include-schedule` to opt in.

Stdlib-only (urllib + json + datetime). Prints a timestamped log to
stdout so rows in `_index.tsv` can be matched to walk steps after
the fact.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


def _request(
    method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 15.0
) -> dict[str, Any]:
    """Issue a JSON HTTP request and return the parsed response body.
    Non-2xx responses raise — we want the walk to stop and surface the
    failure rather than continue with a bad state."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"accept": "application/json"}
    if data is not None:
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if not raw:
            return {}
        return json.loads(raw)


def _log(step: int, total: int, name: str, summary: str) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    print(f"[{ts}] {step:>2}/{total}  {name:<24} {summary}", flush=True)


def _pick_alt_mode(current: str) -> str:
    """Pick a mode different from the current one, prefer fanonly →
    auto → off so the walk doesn't swing HVAC hard. If current is
    already fanonly, fall to auto."""
    priority = ["fanonly", "auto", "off", "cool", "heat"]
    for m in priority:
        if m != current:
            return m
    return "auto"


def _build_plan(
    state: dict[str, Any],
    zone_id: str,
    include_schedule: bool,
) -> list[tuple[str, Callable[[], str]]]:
    """Materialize the walk as a list of (name, fn) — each fn issues
    one mutation and returns a short summary for the log. We freeze
    the 'original' values up front so the reverse steps restore to
    what was seen at the start, not to whatever the last mutation
    happened to leave."""
    base_url = state["_base_url"]
    system = state["system"]
    orig_mode = system["mode"]
    alt_mode = _pick_alt_mode(orig_mode)

    zone = next((z for z in state["zones"] if z["id"] == zone_id), None)
    if zone is None:
        raise SystemExit(f"zone {zone_id} not found in /v1/state — available: "
                         f"{[z['id'] for z in state['zones']]}")
    orig_heat = zone.get("heatSetpoint") or 68
    orig_cool = zone.get("coolSetpoint") or 76

    humidity = _request("GET", f"{base_url}/v1/system/humidity")
    orig_hum_home = humidity.get("targetHome") or 45

    activities = _request("GET", f"{base_url}/v1/zones/{zone_id}/activities")
    home = next((a for a in activities if a["id"] == "home"), None)
    orig_home_heat = (home or {}).get("heat") or 68
    orig_home_cool = (home or {}).get("cool") or 76

    now = datetime.now(timezone.utc).replace(microsecond=0)
    vac_start = now.isoformat()
    vac_end = (now + timedelta(days=1)).isoformat()

    def _zone_setpoints_bump():
        r = _request(
            "PATCH", f"{base_url}/v1/zones/{zone_id}",
            {"heat": orig_heat + 1, "cool": orig_cool + 1},
        )
        return f"heat={r.get('heatSetpoint')} cool={r.get('coolSetpoint')} (bump +1)"

    def _zone_setpoints_restore():
        r = _request(
            "PATCH", f"{base_url}/v1/zones/{zone_id}",
            {"heat": orig_heat, "cool": orig_cool, "activateHold": False},
        )
        return f"restored heat={orig_heat} cool={orig_cool}"

    def _zone_hold_set():
        r = _request(
            "PUT", f"{base_url}/v1/zones/{zone_id}/hold",
            {"activity": "manual"},
        )
        return f"hold activity={r['hold']['activity']} (forever)"

    def _zone_hold_clear():
        r = _request("DELETE", f"{base_url}/v1/zones/{zone_id}/hold")
        return f"hold active={r['hold']['active']}"

    def _system_hold_set():
        r = _request(
            "PUT", f"{base_url}/v1/system/hold",
            {"activity": "home"},
        )
        return f"whole-house hold activity={r['hold']['activity']}"

    def _system_hold_clear():
        r = _request("DELETE", f"{base_url}/v1/system/hold")
        return f"whole-house hold active={r['hold']['active']}"

    def _system_mode_flip():
        r = _request("PATCH", f"{base_url}/v1/system", {"mode": alt_mode})
        return f"{orig_mode} -> {r['mode']}"

    def _system_mode_restore():
        r = _request("PATCH", f"{base_url}/v1/system", {"mode": orig_mode})
        return f"{alt_mode} -> {r['mode']}"

    def _vacation_enable():
        r = _request(
            "PATCH", f"{base_url}/v1/system/vacation",
            {"active": True, "start": vac_start, "end": vac_end},
        )
        return f"active={r['active']} window=24h"

    def _vacation_disable():
        r = _request(
            "PATCH", f"{base_url}/v1/system/vacation",
            {"active": False},
        )
        return f"active={r['active']}"

    def _humidity_bump():
        r = _request(
            "PATCH", f"{base_url}/v1/system/humidity",
            {"targetHome": min(orig_hum_home + 5, 60)},
        )
        return f"targetHome={r.get('targetHome')} (bump +5)"

    def _humidity_restore():
        r = _request(
            "PATCH", f"{base_url}/v1/system/humidity",
            {"targetHome": orig_hum_home},
        )
        return f"targetHome={r.get('targetHome')} (restored)"

    def _activity_bump():
        r = _request(
            "PATCH", f"{base_url}/v1/zones/{zone_id}/activities/home",
            {"heat": orig_home_heat + 1, "cool": orig_home_cool + 1},
        )
        return f"home heat={r.get('heat')} cool={r.get('cool')} (bump +1)"

    def _activity_restore():
        r = _request(
            "PATCH", f"{base_url}/v1/zones/{zone_id}/activities/home",
            {"heat": orig_home_heat, "cool": orig_home_cool},
        )
        return f"home heat={r.get('heat')} cool={r.get('cool')} (restored)"

    plan: list[tuple[str, Callable[[], str]]] = [
        ("zone_setpoints_set",   _zone_setpoints_bump),
        ("zone_hold_set",        _zone_hold_set),
        ("zone_hold_clear",      _zone_hold_clear),
        ("system_hold_set",      _system_hold_set),
        ("system_hold_clear",    _system_hold_clear),
        ("system_mode_set",      _system_mode_flip),
        ("system_mode_set:rev",  _system_mode_restore),
        ("vacation_set:on",      _vacation_enable),
        ("vacation_set:off",     _vacation_disable),
        ("humidity_set",         _humidity_bump),
        ("humidity_set:rev",     _humidity_restore),
        ("activity_set",         _activity_bump),
        ("activity_set:rev",     _activity_restore),
        ("zone_setpoints_set:rev", _zone_setpoints_restore),
    ]

    if include_schedule:
        # Schedule walk: read current, swap the first two periods' start
        # times on Monday, PUT back, then restore. The swap is minimal
        # so if the capture stops mid-walk the state is near the original.
        def _schedule_swap(rev: bool = False):
            sched = _request("GET", f"{base_url}/v1/zones/{zone_id}/schedule")
            days = sched["days"]
            for d in days:
                if d["day"].lower() == "monday" and len(d["periods"]) >= 2:
                    p0, p1 = d["periods"][0], d["periods"][1]
                    p0["time"], p1["time"] = p1["time"], p0["time"]
                    break
            _request(
                "PUT", f"{base_url}/v1/zones/{zone_id}/schedule",
                {"days": days},
            )
            return "swapped Monday periods 0/1" if not rev else "restored Monday order"

        plan.append(("schedule_set", lambda: _schedule_swap(rev=False)))
        plan.append(("schedule_set:rev", lambda: _schedule_swap(rev=True)))

    return plan


def walk(base_url: str, zone_id: str, pace_s: float, include_schedule: bool) -> int:
    state = _request("GET", f"{base_url}/v1/state")
    state["_base_url"] = base_url
    plan = _build_plan(state, zone_id, include_schedule)

    print(
        f"\nmutation walk — {len(plan)} steps, {pace_s:.0f}s pacing, "
        f"zone={zone_id}, base={base_url}\n",
        flush=True,
    )

    failures: list[tuple[str, str]] = []
    for i, (name, fn) in enumerate(plan, 1):
        try:
            summary = fn()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            summary = f"FAIL HTTP {e.code}: {body}"
            failures.append((name, summary))
        except Exception as e:  # noqa: BLE001
            summary = f"FAIL {type(e).__name__}: {e}"
            failures.append((name, summary))
        _log(i, len(plan), name, summary)
        if i < len(plan):
            time.sleep(pace_s)

    print("", flush=True)
    if failures:
        print(f"{len(failures)} step(s) failed:", flush=True)
        for name, summary in failures:
            print(f"  - {name}: {summary}", flush=True)
        return 1
    print("all steps ok", flush=True)
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Walk each /v1/* mutation kind once in each direction "
            "(set + reverse). Use during a capture run to produce a "
            "temporally-separated fixture-ready mutation sequence, or "
            "as a post-cutover API smoke test."
        ),
    )
    p.add_argument(
        "--base-url",
        default="http://localhost:3001",
        help="Addon base URL (default: http://localhost:3001)",
    )
    p.add_argument(
        "--zone-id",
        default="1",
        help="Zone to exercise (default: 1)",
    )
    p.add_argument(
        "--pace",
        type=float,
        default=60.0,
        help="Seconds between steps (default: 60). Shorter pacing packs "
             "the walk but can interleave a mutation's telemetry echo "
             "with the next mutation's write in the capture table.",
    )
    p.add_argument(
        "--include-schedule",
        action="store_true",
        help="Include a minimal schedule_set round-trip (swap two period "
             "times on Monday, then swap back). Off by default — overwrites "
             "the full 7-day program and the restore is best-effort.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    return walk(args.base_url, args.zone_id, args.pace, args.include_schedule)


if __name__ == "__main__":
    raise SystemExit(main())
