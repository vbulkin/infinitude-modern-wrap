"""Runtime settings loaded from environment variables.

Mirrors the options declared in config.yaml. The HA supervisor injects
add-on options into the container as JSON at /data/options.json; we
read env vars here to keep Phase 2 deployable outside of HA too.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # Whether the implicit Carrier-cloud bridge runs. When False,
    # the addon never reaches out to api.ing.carrier.com — fully
    # offline-first operation, MyInfinity-app round-trips disabled.
    # Replaces the alpha.0-47 numeric `pass_reqs` cadence; we no
    # longer cache/throttle Carrier traffic (Carrier's own pingRate
    # signal handles device-side rate-limiting natively, so a second
    # throttle on our side was overruling Carrier's authority — see
    # CarrierBridge module docstring for the rationale).
    carrier_bridge: bool
    log_level: str
    commit_sha: str
    built_at: str
    db_path: str


def _default_db_path() -> str:
    # HA addon: /data is the supervisor-backed persistent volume. Outside
    # HA (dev, CI) that path doesn't exist and we'd fail to create the
    # parent, so fall back to a repo-local ./data/ dir.
    if Path("/data").is_dir():
        return "/data/infinitude.db"
    return "./data/infinitude.db"


def _bool_env(name: str, default: bool) -> bool:
    """Parse an env var as a permissive bool — accepts 1/0, true/false,
    yes/no, on/off (case-insensitive)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y", "t"}


def load_settings() -> Settings:
    return Settings(
        # Backward compat: if the operator's options.json still has
        # the old `pass_reqs` knob, treat any value > 0 as "bridge
        # enabled" so an old deployment doesn't suddenly lose Carrier
        # connectivity on upgrade. Once HA writes the new boolean,
        # it overrides.
        carrier_bridge=_bool_env(
            "CARRIER_BRIDGE",
            default=int(os.environ.get("PASS_REQS", "1")) > 0,
        ),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
        commit_sha=os.environ.get("COMMIT_SHA", "dev"),
        built_at=os.environ.get("BUILT_AT", "1970-01-01T00:00:00Z"),
        db_path=os.environ.get("INFINITUDE_DB_PATH", _default_db_path()),
    )
