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
    pass_reqs: int
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


def load_settings() -> Settings:
    return Settings(
        pass_reqs=int(os.environ.get("PASS_REQS", "120")),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
        commit_sha=os.environ.get("COMMIT_SHA", "dev"),
        built_at=os.environ.get("BUILT_AT", "1970-01-01T00:00:00Z"),
        db_path=os.environ.get("INFINITUDE_DB_PATH", _default_db_path()),
    )
