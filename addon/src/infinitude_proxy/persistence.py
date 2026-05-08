"""SQLite-backed persistence for the proxy.

Two concerns, per DESIGN.md §11:
  1. state_cache   — the latest config / idu / odu XML the thermostat
                     has posted (or we've mutated locally). Read on
                     startup so /v1/state and GET /systems/{serial}/config
                     work immediately without waiting for a fresh POST.
  2. pending_writes — northbound mutations that haven't yet landed on
                     the thermostat. Each is a typed, replayable row.
                     Survives proxy restart; marked applied when the
                     thermostat GETs /systems/{serial}/config (pull-
                     observed semantic — see DESIGN.md §4.3 for the
                     stricter "confirmation" semantic we may upgrade
                     to later).

Single-thermostat deployment (non-goal from DESIGN.md §3) — the
`serial` column is retained for data hygiene and future multi-unit
support, but queries are not filtered by it in the common case.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 4

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS state_cache (
    serial        TEXT PRIMARY KEY,
    config_xml    BLOB,
    idu_xml       BLOB,
    odu_xml       BLOB,
    config_dirty  INTEGER NOT NULL DEFAULT 0,
    updated_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_writes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    serial       TEXT NOT NULL,
    kind         TEXT NOT NULL,
    target       TEXT,
    payload_json TEXT NOT NULL,
    created_at   REAL NOT NULL,
    applied_at   REAL
);

CREATE INDEX IF NOT EXISTS idx_pending_unapplied
    ON pending_writes(serial, created_at)
    WHERE applied_at IS NULL;
"""

# v2: debug traffic capture. `direction` is the union of three values
# set by the emitter: 'southbound' (thermostat → proxy), 'northbound'
# (HA/browser → proxy), 'carrier_out' (proxy → carrier.com forward-proxy
# passthrough, not yet wired). Body columns are BLOB so we retain raw
# bytes regardless of content-type; NULL when empty. `captured_at` is
# unix-seconds like state_cache.updated_at, not an ISO string, so range
# filters are pure numeric compares.
_SCHEMA_V2_ADD = """
CREATE TABLE IF NOT EXISTS capture_traffic (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       REAL NOT NULL,
    direction         TEXT NOT NULL,
    method            TEXT NOT NULL,
    path              TEXT NOT NULL,
    query             TEXT,
    status_code       INTEGER NOT NULL,
    req_content_type  TEXT,
    req_body          BLOB,
    resp_content_type TEXT,
    resp_body         BLOB,
    duration_ms       INTEGER
);

CREATE INDEX IF NOT EXISTS idx_capture_time ON capture_traffic(captured_at);
CREATE INDEX IF NOT EXISTS idx_capture_path ON capture_traffic(path);
"""

# v3: persist ODU and IDU live-status snapshots so HA's compressor-stage
# / blower-RPM / refrigerant-pressure sensors keep their last-known
# values across an addon restart. Pre-v3 these were in-memory only
# (state_store.py) — restart blanked them until the unit's next status
# POST, which only happens while the equipment is actively running. A
# user looking at the dashboard right after a restart on an idle system
# would see a row of `unavailable` cells. Same data shape as
# config/idu/odu — raw POST-body XML, COALESCE-upserted, NULL until
# the first status arrives.
_SCHEMA_V3_ADD = """
ALTER TABLE state_cache ADD COLUMN odu_status_xml BLOB;
ALTER TABLE state_cache ADD COLUMN idu_status_xml BLOB;
"""

# v4 (alpha.53): full request + response header capture, for the
# investigation into why our synthetic Carrier-bound POSTs sometimes
# 401 while the thermostat's real-time calls succeed. Pre-v4 we only
# stored req_content_type — useless for diffing thermostat-real-time
# vs addon-replay headers. With v4 the capture_traffic table stores
# the raw header dict (JSON-encoded) for both directions, so the
# investigation can compare what's actually different on the wire
# without theorizing about route scope, TTLs, etc.
#
# `req_headers_json` and `resp_headers_json` are TEXT (JSON object
# {name: value}). NULL when the emitter didn't capture them (pre-v4
# entries, or when capture is disabled mid-request). Capture
# middleware + CarrierBridge + ForwardProxy all populate these.
_SCHEMA_V4_ADD = """
ALTER TABLE capture_traffic ADD COLUMN req_headers_json TEXT;
ALTER TABLE capture_traffic ADD COLUMN resp_headers_json TEXT;
"""


@dataclass
class StateSnapshot:
    """A point-in-time view of the cached wire bytes for one serial."""
    serial: str
    config_xml: bytes | None
    idu_xml: bytes | None
    odu_xml: bytes | None
    config_dirty: bool
    updated_at: float
    # v3 (alpha.50): live-status snapshots persisted so HA stage /
    # RPM / pressure sensors survive addon restarts.
    odu_status_xml: bytes | None = None
    idu_status_xml: bytes | None = None


@dataclass
class PendingWrite:
    """One queued northbound mutation, pre- or post-apply."""
    id: int
    serial: str
    kind: str
    target: str | None
    payload: dict
    created_at: float
    applied_at: float | None


class Persistence:
    """Async SQLite wrapper. Open once per app, close on shutdown.

    All methods are coroutines; the underlying connection is serialized
    by aiosqlite's internal thread. Concurrent callers are safe.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    @classmethod
    async def open(cls, path: Path | str) -> "Persistence":
        """Open (or create) the DB file and run migrations.

        `path` may be `:memory:` for ephemeral/test use. Parent
        directory is created for on-disk paths.
        """
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(path)
        # WAL = crash-safe journaling + better concurrency than default
        # rollback-journal mode. foreign_keys on for future FK use.
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        await conn.commit()
        instance = cls(conn)
        await instance._migrate()
        return instance

    async def close(self) -> None:
        await self._conn.close()

    async def _migrate(self) -> None:
        await self._conn.executescript(_SCHEMA_V1)
        async with self._conn.execute(
            "SELECT version FROM schema_version"
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            # Fresh DB: apply every version's additive DDL before
            # stamping the version row.
            await self._conn.executescript(_SCHEMA_V2_ADD)
            await self._conn.executescript(_SCHEMA_V3_ADD)
            await self._conn.executescript(_SCHEMA_V4_ADD)
            await self._conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            await self._conn.commit()
            logger.info("persistence: initialized schema v%d", SCHEMA_VERSION)
            return
        current = row[0]
        if current > SCHEMA_VERSION:
            raise RuntimeError(
                f"persistence: db schema version {current} is newer than"
                f" this build ({SCHEMA_VERSION}); downgrade not supported"
            )
        if current < SCHEMA_VERSION:
            # Forward-only migrations. IF NOT EXISTS in DDL makes each
            # step idempotent if interrupted; ALTER TABLE doesn't
            # support IF NOT EXISTS so we wrap v3's add-columns in a
            # PRAGMA-table-info check.
            if current < 2:
                await self._conn.executescript(_SCHEMA_V2_ADD)
            if current < 3:
                # SQLite has no ALTER COLUMN IF NOT EXISTS, so check
                # the table_info pragma first to make this re-runnable
                # on a partial v3 (rare — the two ALTERs are atomic
                # under the same connection — but cheap insurance).
                async with self._conn.execute(
                    "PRAGMA table_info(state_cache)"
                ) as cur:
                    cols = {r[1] for r in await cur.fetchall()}
                if "odu_status_xml" not in cols:
                    await self._conn.execute(
                        "ALTER TABLE state_cache ADD COLUMN odu_status_xml BLOB"
                    )
                if "idu_status_xml" not in cols:
                    await self._conn.execute(
                        "ALTER TABLE state_cache ADD COLUMN idu_status_xml BLOB"
                    )
            if current < 4:
                # Same idempotent ALTER pattern: check table_info on
                # capture_traffic, add the header columns if missing.
                async with self._conn.execute(
                    "PRAGMA table_info(capture_traffic)"
                ) as cur:
                    cols = {r[1] for r in await cur.fetchall()}
                if "req_headers_json" not in cols:
                    await self._conn.execute(
                        "ALTER TABLE capture_traffic ADD COLUMN req_headers_json TEXT"
                    )
                if "resp_headers_json" not in cols:
                    await self._conn.execute(
                        "ALTER TABLE capture_traffic ADD COLUMN resp_headers_json TEXT"
                    )
            await self._conn.execute(
                "UPDATE schema_version SET version = ?", (SCHEMA_VERSION,)
            )
            await self._conn.commit()
            logger.info(
                "persistence: migrated schema v%d → v%d", current, SCHEMA_VERSION
            )

    # ── state_cache ──────────────────────────────────────────────────

    async def save_config(self, serial: str, xml: bytes) -> None:
        """Upsert the config XML for a serial. Called on both apply_config
        (thermostat POST) and mutate_config (NB write)."""
        await self._upsert_state(serial, config_xml=xml)

    async def save_idu(self, serial: str, xml: bytes) -> None:
        await self._upsert_state(serial, idu_xml=xml)

    async def save_odu(self, serial: str, xml: bytes) -> None:
        await self._upsert_state(serial, odu_xml=xml)

    async def save_odu_status(self, serial: str, xml: bytes) -> None:
        """Persist the most recent ODU live-status XML so HA's
        compressor-stage / RPM / pressure / superheat sensors survive
        an addon restart. Each new POST supersedes the prior — we
        only ever care about latest, not history."""
        await self._upsert_state(serial, odu_status_xml=xml)

    async def save_idu_status(self, serial: str, xml: bytes) -> None:
        """Persist the most recent IDU live-status XML so HA's
        blower-RPM / airflow / static-pressure sensors survive an
        addon restart. Each new POST supersedes the prior."""
        await self._upsert_state(serial, idu_status_xml=xml)

    async def save_config_dirty(self, serial: str, dirty: bool) -> None:
        """Persist the dirty flag so a proxy restart doesn't silently
        re-clear it mid-cycle (the thermostat has already been told to
        pull — if we forget, the pending edit is lost). Row is created
        if it doesn't exist yet; other columns are preserved."""
        await self._upsert_state(serial, config_dirty=dirty)

    async def _upsert_state(
        self,
        serial: str,
        *,
        config_xml: bytes | None = None,
        idu_xml: bytes | None = None,
        odu_xml: bytes | None = None,
        odu_status_xml: bytes | None = None,
        idu_status_xml: bytes | None = None,
        config_dirty: bool | None = None,
    ) -> None:
        now = time.time()
        # Partial upsert — only overwrite the column(s) the caller passed.
        # COALESCE against excluded.* so e.g. save_idu doesn't clobber
        # the existing config_xml with NULL. config_dirty is coerced to
        # 0/1 (SQLite has no native bool) and encoded as NULL-when-unset
        # so the same COALESCE trick works.
        dirty_val: int | None = (
            None if config_dirty is None else (1 if config_dirty else 0)
        )
        await self._conn.execute(
            """
            INSERT INTO state_cache
                (serial, config_xml, idu_xml, odu_xml,
                 odu_status_xml, idu_status_xml,
                 config_dirty, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, 0), ?)
            ON CONFLICT(serial) DO UPDATE SET
                config_xml     = COALESCE(excluded.config_xml,     state_cache.config_xml),
                idu_xml        = COALESCE(excluded.idu_xml,        state_cache.idu_xml),
                odu_xml        = COALESCE(excluded.odu_xml,        state_cache.odu_xml),
                odu_status_xml = COALESCE(excluded.odu_status_xml, state_cache.odu_status_xml),
                idu_status_xml = COALESCE(excluded.idu_status_xml, state_cache.idu_status_xml),
                config_dirty   = COALESCE(?, state_cache.config_dirty),
                updated_at     = excluded.updated_at
            """,
            (
                serial, config_xml, idu_xml, odu_xml,
                odu_status_xml, idu_status_xml,
                dirty_val, now, dirty_val,
            ),
        )
        await self._conn.commit()

    _STATE_COLS = (
        "serial, config_xml, idu_xml, odu_xml, "
        "odu_status_xml, idu_status_xml, "
        "config_dirty, updated_at"
    )

    @staticmethod
    def _row_to_snapshot(row: tuple) -> "StateSnapshot":
        return StateSnapshot(
            serial=row[0],
            config_xml=row[1],
            idu_xml=row[2],
            odu_xml=row[3],
            odu_status_xml=row[4],
            idu_status_xml=row[5],
            config_dirty=bool(row[6]),
            updated_at=row[7],
        )

    async def load(self, serial: str) -> StateSnapshot | None:
        async with self._conn.execute(
            f"SELECT {self._STATE_COLS} FROM state_cache WHERE serial = ?",
            (serial,),
        ) as cursor:
            row = await cursor.fetchone()
        return self._row_to_snapshot(row) if row else None

    async def load_any(self) -> StateSnapshot | None:
        """Return the most-recently-updated cached state across all
        serials. Single-unit deployments hit this on startup before the
        serial is known (no telemetry POST yet); multi-unit callers
        should use load(serial) directly."""
        async with self._conn.execute(
            f"SELECT {self._STATE_COLS} FROM state_cache "
            "ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
        return self._row_to_snapshot(row) if row else None

    # ── pending_writes ───────────────────────────────────────────────

    async def enqueue_write(
        self,
        serial: str,
        kind: str,
        target: str | None,
        payload: dict,
    ) -> int:
        """Append a pending mutation. Returns the row id so callers can
        correlate enqueue → replay → mark_applied."""
        now = time.time()
        cursor = await self._conn.execute(
            """
            INSERT INTO pending_writes
                (serial, kind, target, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (serial, kind, target, json.dumps(payload, sort_keys=True), now),
        )
        await self._conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    async def mark_applied(self, ids: list[int]) -> None:
        """Mark rows as applied. Idempotent — already-applied rows are
        no-ops (applied_at isn't overwritten)."""
        if not ids:
            return
        now = time.time()
        placeholders = ",".join("?" * len(ids))
        await self._conn.execute(
            f"UPDATE pending_writes "
            f"SET applied_at = ? "
            f"WHERE id IN ({placeholders}) AND applied_at IS NULL",
            (now, *ids),
        )
        await self._conn.commit()

    async def mark_all_applied(self, serial: str) -> list[int]:
        """Pull-observed semantic: the thermostat GET /config proves it
        saw the mutated tree. Mark every currently-unapplied row for
        this serial as applied. Returns the affected ids for logging."""
        now = time.time()
        async with self._conn.execute(
            "SELECT id FROM pending_writes "
            "WHERE serial = ? AND applied_at IS NULL",
            (serial,),
        ) as cursor:
            rows = await cursor.fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        await self._conn.execute(
            f"UPDATE pending_writes "
            f"SET applied_at = ? "
            f"WHERE id IN ({placeholders})",
            (now, *ids),
        )
        await self._conn.commit()
        return ids

    async def pending_for_replay(
        self, serial: str, grace_seconds: int = 300,
    ) -> list[PendingWrite]:
        """Pending writes for replay onto an inbound config tree —
        unapplied PLUS recently-applied within the grace window.

        Rationale: when Carrier's tree (or the thermostat's boot tree)
        overwrites our local store, recently-cleared HA-side writes
        must still be merged onto it. Otherwise an HA mutation that
        was already marked applied via pull-observed-clear gets
        silently reverted by upstream stale state. Mirrors the
        legacy Perl Infinitude proxy's "changes-window" behavior.

        Side effect: deletes rows whose `applied_at` is older than the
        grace window so the table doesn't grow unbounded.

        Default grace = 300 s — long enough to absorb the natural
        cadence of Carrier-app round-trips (status mirror → server
        response → /config relay) plus a defensive margin, short
        enough that genuinely-stale rows roll off before they fight
        with newer state.
        """
        now = time.time()
        threshold = now - grace_seconds
        # Lazy GC of rows past grace. One DELETE per replay cycle is
        # cheap on local SQLite.
        await self._conn.execute(
            "DELETE FROM pending_writes "
            "WHERE applied_at IS NOT NULL AND applied_at < ?",
            (threshold,),
        )
        await self._conn.commit()
        async with self._conn.execute(
            "SELECT id, serial, kind, target, payload_json, "
            "       created_at, applied_at "
            "FROM pending_writes "
            "WHERE serial = ? AND (applied_at IS NULL OR applied_at >= ?) "
            "ORDER BY created_at ASC",
            (serial, threshold),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            PendingWrite(
                id=r[0],
                serial=r[1],
                kind=r[2],
                target=r[3],
                payload=json.loads(r[4]),
                created_at=r[5],
                applied_at=r[6],
            )
            for r in rows
        ]

    async def pending(self, serial: str | None = None) -> list[PendingWrite]:
        """All currently-unapplied writes, oldest first. If serial is
        given, filter to that unit; otherwise every unit's queue."""
        if serial is None:
            query = (
                "SELECT id, serial, kind, target, payload_json, "
                "       created_at, applied_at "
                "FROM pending_writes "
                "WHERE applied_at IS NULL "
                "ORDER BY created_at ASC"
            )
            args: tuple = ()
        else:
            query = (
                "SELECT id, serial, kind, target, payload_json, "
                "       created_at, applied_at "
                "FROM pending_writes "
                "WHERE serial = ? AND applied_at IS NULL "
                "ORDER BY created_at ASC"
            )
            args = (serial,)
        async with self._conn.execute(query, args) as cursor:
            rows = await cursor.fetchall()
        return [
            PendingWrite(
                id=r[0],
                serial=r[1],
                kind=r[2],
                target=r[3],
                payload=json.loads(r[4]),
                created_at=r[5],
                applied_at=r[6],
            )
            for r in rows
        ]

    async def unapplied_count(self, serial: str | None = None) -> int:
        """Number of pending writes. Cheap — used by /v1/healthz and by
        the status handler to decide if a directive should signal."""
        if serial is None:
            query = (
                "SELECT COUNT(*) FROM pending_writes WHERE applied_at IS NULL"
            )
            args: tuple = ()
        else:
            query = (
                "SELECT COUNT(*) FROM pending_writes "
                "WHERE serial = ? AND applied_at IS NULL"
            )
            args = (serial,)
        async with self._conn.execute(query, args) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    # ── capture_traffic ──────────────────────────────────────────────

    async def capture_insert(
        self,
        *,
        captured_at: float,
        direction: str,
        method: str,
        path: str,
        query: str | None,
        status_code: int,
        req_content_type: str | None,
        req_body: bytes | None,
        resp_content_type: str | None,
        resp_body: bytes | None,
        duration_ms: int | None,
        max_rows: int | None = None,
        req_headers: dict[str, str] | None = None,
        resp_headers: dict[str, str] | None = None,
    ) -> int:
        """Insert one traffic row and, when max_rows is set, trim the
        oldest rows down to the cap in the same transaction.

        The cap-trim is done here (not on a background timer) so callers
        can't observe a window where the table exceeds the cap. Cost of
        the extra DELETE on every insert is negligible at expected
        cadences (~10/minute sustained).

        v4 (alpha.53): `req_headers` / `resp_headers` are JSON-encoded
        and stored on the row so the diagnostic "what's different
        between thermostat-real-time and addon-replay" investigation
        has actual data to compare against. None preserved as NULL —
        consistent with capture-disabled or pre-v4 entries.
        """
        req_h_json = json.dumps(req_headers) if req_headers is not None else None
        resp_h_json = json.dumps(resp_headers) if resp_headers is not None else None
        cursor = await self._conn.execute(
            """
            INSERT INTO capture_traffic
                (captured_at, direction, method, path, query,
                 status_code, req_content_type, req_body,
                 resp_content_type, resp_body, duration_ms,
                 req_headers_json, resp_headers_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                captured_at, direction, method, path, query,
                status_code, req_content_type, req_body,
                resp_content_type, resp_body, duration_ms,
                req_h_json, resp_h_json,
            ),
        )
        assert cursor.lastrowid is not None
        row_id = cursor.lastrowid
        if max_rows is not None and max_rows > 0:
            # Delete everything older than the (max_rows)-th most recent.
            await self._conn.execute(
                """
                DELETE FROM capture_traffic
                WHERE id <= (
                    SELECT id FROM capture_traffic
                    ORDER BY id DESC
                    LIMIT 1 OFFSET ?
                )
                """,
                (max_rows,),
            )
        await self._conn.commit()
        return row_id

    async def capture_list(
        self,
        *,
        limit: int = 100,
        since_id: int | None = None,
        direction: str | None = None,
        method: str | None = None,
        path_prefix: str | None = None,
    ) -> list[dict]:
        """Paginated metadata listing (no bodies — keeps responses small).

        Filter semantics:
          - since_id: return rows with id > since_id (exclusive). Pairs
            with the max(id) of a prior page for cursor pagination.
          - path_prefix: LIKE '<prefix>%' — useful for narrowing to e.g.
            '/systems/' (southbound) or '/v1/' (northbound).

        Returns newest-first. The debug UI can reverse client-side if
        chronological order is preferred.
        """
        clauses: list[str] = []
        args: list = []
        if since_id is not None:
            clauses.append("id > ?")
            args.append(since_id)
        if direction is not None:
            clauses.append("direction = ?")
            args.append(direction)
        if method is not None:
            clauses.append("method = ?")
            args.append(method.upper())
        if path_prefix is not None:
            clauses.append("path LIKE ?")
            args.append(path_prefix + "%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        args.append(limit)
        query = (
            "SELECT id, captured_at, direction, method, path, query, "
            "       status_code, req_content_type, "
            "       LENGTH(req_body) AS req_bytes, resp_content_type, "
            "       LENGTH(resp_body) AS resp_bytes, duration_ms, "
            "       req_headers_json, resp_headers_json "
            f"FROM capture_traffic {where} "
            "ORDER BY id DESC LIMIT ?"
        )
        async with self._conn.execute(query, args) as cursor:
            rows = await cursor.fetchall()
        cols = [
            "id", "captured_at", "direction", "method", "path", "query",
            "status_code", "req_content_type", "req_bytes",
            "resp_content_type", "resp_bytes", "duration_ms",
            "req_headers_json", "resp_headers_json",
        ]
        return [dict(zip(cols, r)) for r in rows]

    async def capture_get(self, row_id: int) -> dict | None:
        """Full row including body BLOBs. Caller chooses how to encode
        (text vs base64) based on content-type."""
        async with self._conn.execute(
            "SELECT id, captured_at, direction, method, path, query, "
            "       status_code, req_content_type, req_body, "
            "       resp_content_type, resp_body, duration_ms, "
            "       req_headers_json, resp_headers_json "
            "FROM capture_traffic WHERE id = ?",
            (row_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        cols = [
            "id", "captured_at", "direction", "method", "path", "query",
            "status_code", "req_content_type", "req_body",
            "resp_content_type", "resp_body", "duration_ms",
            "req_headers_json", "resp_headers_json",
        ]
        return dict(zip(cols, row))

    async def capture_stats(self) -> dict:
        """Summary for the debug status endpoint — cheap aggregate."""
        async with self._conn.execute(
            "SELECT COUNT(*), MIN(captured_at), MAX(captured_at), "
            "       COALESCE(SUM(LENGTH(req_body)), 0) + "
            "       COALESCE(SUM(LENGTH(resp_body)), 0) "
            "FROM capture_traffic"
        ) as cursor:
            row = await cursor.fetchone()
        count = int(row[0]) if row else 0
        return {
            "rowCount": count,
            "oldestAt": row[1] if row and count else None,
            "newestAt": row[2] if row and count else None,
            "totalBytes": int(row[3]) if row else 0,
        }

    async def capture_flush(self) -> int:
        """Delete every capture row. Returns how many were removed so the
        debug endpoint can echo the effect."""
        cursor = await self._conn.execute(
            "DELETE FROM capture_traffic"
        )
        await self._conn.commit()
        return cursor.rowcount or 0

    async def oldest_pending_age_seconds(
        self, serial: str | None = None
    ) -> float | None:
        """Age (s) of the oldest unapplied write, or None if none pending.
        Feeds /v1/healthz.stateStore.oldestPendingPushAgeSeconds."""
        if serial is None:
            query = (
                "SELECT MIN(created_at) FROM pending_writes "
                "WHERE applied_at IS NULL"
            )
            args: tuple = ()
        else:
            query = (
                "SELECT MIN(created_at) FROM pending_writes "
                "WHERE serial = ? AND applied_at IS NULL"
            )
            args = (serial,)
        async with self._conn.execute(query, args) as cursor:
            row = await cursor.fetchone()
        if row is None or row[0] is None:
            return None
        return time.time() - float(row[0])
