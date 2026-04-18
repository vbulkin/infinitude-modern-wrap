# Infinitude Modern Proxy — Design Document

Status: **Draft / proposal**
Target branch: `design/openapi-rewrite`
Companion: [`openapi.yaml`](./openapi.yaml)

---

## 1. Summary

Replace the existing Perl/Mojolicious Infinitude proxy with a Python service that:
- Retains 100% of the thermostat-facing protocol and Carrier cloud passthrough behavior (non-negotiable).
- Exposes a first-class, OpenAPI-described northbound HTTP API for the HA integration and web UI.
- Ships as a Home Assistant add-on (Docker/Python), with the current modern web UI as the only user interface.
- Drops the RS485/serial_tty code path entirely — network only.
- Drops the legacy `native.html` UI (Infinitude's original Perl-rendered pages).
- Exposes a comprehensive `/healthz` endpoint for diagnostics.

The rewrite is primarily a **northbound API modernization** plus a **language migration**. Thermostat compatibility is preserved by re-implementing exactly the southbound request/response shapes the thermostat expects.

---

## 2. Goals

1. **API clarity** — typed resources, flat JSON, no XML::Simple array-wrapped scalars, explicit error model.
2. **Schema contract** — OpenAPI 3.1 is the source of truth; Pydantic models generated from / validated against it.
3. **Shared types** — one Pydantic model set used by both the add-on and the HA integration, eliminating today's hand-typed field parsing in `coordinator.py`.
4. **Observability** — structured logs, health probe, metrics hooks, stale-data detection surfaced in the API.
5. **Live updates** — Server-Sent Events channel so the HA integration and web UI can subscribe to state changes instead of 30-second polling.
6. **Thermostat compatibility** — drop-in replacement: point existing thermostat DNS at the new add-on, no reflashing required.

## 3. Non-goals

- **Serial / RS485 connectivity.** Dropped. Network-only installations are the documented path.
- **Infinitude native UI.** Dropped. The modern HTML UI (`infinitude/infinitude-ui.html`) becomes the sole UI.
- **Backwards-compat with legacy `/api/*?mode=...` query-string endpoints.** The old endpoints are removed; the HA integration updates to the new API in the same release cycle. No dual-stack period.
- **Multi-thermostat support.** Single thermostat per proxy instance, same as today.
- **Non-Home-Assistant consumers.** The API is public and documented, but we do not commit to stability beyond the OpenAPI contract.

## 4. Architecture

```
                                  ┌──────────────────────────────────────┐
                                  │ Home Assistant host                  │
 ┌──────────────┐                 │                                      │
 │ Thermostat   │  POST telemetry │  ┌──────────────────────────────┐    │
 │ (Carrier/    │────────────────▶│  │  Add-on: infinitude-proxy    │    │
 │  Bryant)     │◀────────────────│  │  (Python / FastAPI / aiohttp)│    │
 └──────────────┘  response XML   │  │                              │    │
         ▲                        │  │  ┌────────────────────────┐  │    │
         │                        │  │  │ Southbound: thermostat │  │    │
         │                        │  │  │ XML request handler    │  │    │
         │                        │  │  └────────┬───────────────┘  │    │
         │                        │  │           │ cache             │    │
         │                        │  │  ┌────────▼───────────────┐   │    │
         │ passthrough            │  │  │ In-memory state + SQLite│◀─┼────┼─── HA integration
         │ (pass_reqs cadence)    │  │  │ persistence            │   │    │    (HTTP + SSE)
         │                        │  │  └────────┬───────────────┘   │    │
         │                        │  │           │                    │    │
         │                        │  │  ┌────────▼───────────────┐   │    │
         ▼                        │  │  │ Northbound: OpenAPI    │◀──┼────┼─── Web UI (same pod,
 ┌──────────────┐   HTTPS         │  │  │ (FastAPI router)       │   │    │    /ingress path)
 │ Carrier      │◀────────────────│  │  └────────────────────────┘   │    │
 │ cloud        │                 │  │                              │    │
 └──────────────┘                 │  └──────────────────────────────┘    │
                                  └──────────────────────────────────────┘
```

### 4.1 Component responsibilities

| Component | Responsibility |
|---|---|
| **Southbound handler** | Accepts thermostat HTTP POSTs, decodes Carrier's XML payloads, updates in-memory state, returns the XML responses the thermostat expects. Exactly matches upstream Infinitude's wire protocol. |
| **Passthrough scheduler** | On the cadence configured by `pass_reqs`, replays the last thermostat request to Carrier's cloud and records the response. This is transparent to both the thermostat and the northbound API. |
| **State store** | In-memory Python dataclasses / Pydantic models as the hot path; SQLite snapshot for restart continuity. Persists only the latest known state (no history). |
| **Northbound API** | FastAPI app implementing the OpenAPI spec. Reads from the state store for queries; writes to the state store AND schedules a "push to thermostat" for mutations. |
| **SSE channel** | `GET /v1/events` streams state deltas so consumers don't have to poll. |
| **Web UI** | Served from the same FastAPI process under `/` (or HA ingress). Static assets only — all logic lives client-side and hits the same northbound API. |
| **Health probe** | `GET /v1/healthz` returning component-level status (see §8). |

### 4.2 Data flow — read

1. Thermostat POSTs status every ~90s (Carrier's fixed cadence).
2. Southbound handler parses and writes to state store.
3. State store emits a diff to the SSE channel.
4. HA integration either receives the SSE event or polls `/v1/state` on its own cadence.

### 4.3 Data flow — write (setpoint, hold, schedule)

1. HA integration or web UI PATCHes a resource (e.g. `PATCH /v1/zones/1`).
2. API validates against the Pydantic model and writes to state store.
3. State store marks a "pending-push" flag for the thermostat.
4. Next time the thermostat polls Infinitude (its natural cadence), the southbound handler includes the pending change in the response — same mechanism upstream uses today.
5. Thermostat confirms by including the new value in its next telemetry POST; pending-push flag is cleared.
6. State store emits a diff to SSE.

This matches how upstream Infinitude operates — we inherit Carrier's "thermostat pulls changes" model rather than trying to push.

---

## 5. Technology choices

| Concern | Choice | Rationale |
|---|---|---|
| Language | **Python 3.12+** | Shared types with HA integration; large async HTTP ecosystem; HA add-on tooling friendly. |
| Web framework | **FastAPI** | OpenAPI-native, Pydantic v2 models, SSE via `sse-starlette`. |
| ASGI server | **uvicorn** | Standard, production-quality. |
| XML parsing | **lxml** | Fast, well-maintained, matches Carrier's XML verbosity. |
| Persistence | **SQLite via `aiosqlite`** | Single file, no ops burden, survives add-on restart. |
| Outbound HTTP (Carrier) | **httpx** | Async, HTTP/2 capable if Carrier ever upgrades. |
| Config | Pydantic Settings, env vars + add-on options file. |
| Packaging | HA add-on using `python:3.12-slim` base; multi-arch via buildx. |
| Testing | **pytest** + `pytest-asyncio` + `schemathesis` (OpenAPI property tests). |

Not chosen: Go and Rust — the northbound/southbound code is I/O bound, and Python keeps the door open to sharing code with the HA integration.

---

## 6. Data model

Key design decisions relative to the current upstream:

1. **No array-wrapped scalars.** `mode: "cool"` not `mode: ["cool"]`.
2. **Explicit types.** Temperatures are numbers, booleans are booleans, times are `HH:MM` strings with a documented regex.
3. **Stable IDs.** Zone IDs and activity IDs are strings with explicit patterns; schedule period IDs are `1..N` per day.
4. **Enums.** HVAC mode, activity, fan speed, hold type, conditioning state — all enumerated in OpenAPI and Pydantic.
5. **Separation of concerns:**
   - `System` — mode, outdoor temp, humidifier, local time, diagnostic strings.
   - `Zone` — name, temps, setpoints, humidity, damper, fan, hold, conditioning state.
   - `Activity` — setpoints & fan for a named activity (`home|away|sleep|wake|manual`).
   - `Schedule` — per-zone weekly program: 7 days × up to 5 periods each.
   - `Hold` — zone-level OR whole-house; `until` is either `HH:MM` or `"indefinite"`.

Full schemas live in `openapi.yaml`.

---

## 7. API surface (summary)

Base path: `/v1`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/healthz` | Comprehensive health & freshness snapshot. |
| GET | `/v1/state` | Full aggregate state (system + all zones). |
| GET | `/v1/events` | Server-Sent Events stream of state changes. |
| GET / PATCH | `/v1/system` | System-wide settings (primarily HVAC mode). |
| GET | `/v1/zones` | List all zones. |
| GET / PATCH | `/v1/zones/{zoneId}` | Inspect / update one zone (setpoints, fan). |
| PUT / DELETE | `/v1/zones/{zoneId}/hold` | Set or clear a zone hold. |
| GET / PATCH | `/v1/zones/{zoneId}/activities/{activityId}` | Edit a named activity (setpoints, fan). |
| GET / PUT | `/v1/zones/{zoneId}/schedule` | Get or replace the weekly program for a zone. |
| PUT / DELETE | `/v1/system/hold` | Set or clear the whole-house hold. |
| GET | `/v1/config` | Add-on runtime config (pass_reqs etc.) — read-only. |
| GET | `/v1/version` | Build info: proxy version, API version, commit SHA. |

See `openapi.yaml` for full request/response shapes and error definitions.

### 7.1 Removed vs. legacy

| Legacy | Replacement |
|---|---|
| `GET /systems.json` | `GET /v1/state` (flattened, typed) |
| `GET /status.json` | `GET /v1/state` |
| `GET /Alive` | `GET /v1/healthz` (Carrier status is one field) |
| `PUT /api/config?mode=…` | `PATCH /v1/system` body `{ "mode": "cool" }` |
| `PUT /api/{zone}/hold?activity=…&until=…` | `PUT /v1/zones/{zoneId}/hold` body `{ "activity": "home", "until": "HH:MM" }` |
| `PUT /api/{zone}/activity/{id}?htsp=…` | `PATCH /v1/zones/{zoneId}/activities/{activityId}` body `{ "heat": 68, "cool": 76 }` |
| `PUT /api/config/wholeHouse?hold=on&…` | `PUT /v1/system/hold` body `{ "activity": "away", "until": "17:30" }` |
| `POST /systems/infinitude` (full config dump) | `PUT /v1/zones/{zoneId}/schedule` with structured body |
| `/native.html` | Removed. |

---

## 8. Health probe (`/v1/healthz`)

Returns HTTP 200 always (so external probes don't flip unnecessarily) — the body carries the verdict.

```json
{
  "status": "healthy | degraded | unhealthy",
  "timestamp": "2026-04-17T22:30:00Z",
  "components": {
    "thermostat": {
      "status": "healthy | stale | unreachable",
      "last_contact": "2026-04-17T22:29:42Z",
      "last_contact_age_seconds": 18,
      "expected_interval_seconds": 90,
      "stale_threshold_seconds": 300
    },
    "carrier_cloud": {
      "status": "healthy | degraded | unreachable | disabled",
      "last_success": "2026-04-17T22:28:01Z",
      "last_attempt": "2026-04-17T22:29:00Z",
      "last_error": null,
      "pass_reqs_interval_seconds": 60,
      "consecutive_failures": 0
    },
    "state_store": {
      "status": "healthy | degraded",
      "zones_tracked": 2,
      "pending_pushes": 0,
      "oldest_pending_push_age_seconds": null
    },
    "api": {
      "status": "healthy",
      "uptime_seconds": 3612,
      "active_sse_subscribers": 3
    }
  },
  "version": {
    "proxy": "2.0.0",
    "api": "v1",
    "commit": "abc1234",
    "built_at": "2026-04-01T12:00:00Z"
  }
}
```

`status` roll-up rules:
- `unhealthy` if thermostat is `unreachable` OR state_store is `degraded`.
- `degraded` if Carrier cloud is `unreachable` or `degraded`, OR thermostat is `stale`.
- Otherwise `healthy`.

---

## 9. Events (`/v1/events`)

Server-Sent Events, `Content-Type: text/event-stream`. Each event is a JSON patch-ish envelope:

```
event: state.update
data: {"resource": "zones/1", "changes": {"rt": 72, "zoneconditioning": "idle"}}

event: hold.changed
data: {"resource": "zones/1/hold", "state": "active", "activity": "manual", "until": "19:00"}

event: health.changed
data: {"status": "degraded", "reason": "carrier_cloud.unreachable"}
```

Subscribers reconnect with `Last-Event-ID` to resume.

Initial connect: the server sends a `state.snapshot` event with the full current state, then incremental diffs.

---

## 10. Configuration

### 10.1 Add-on options (`config.yaml`)

| Option | Type | Default | Description | Change vs. today |
|---|---|---|---|---|
| `pass_reqs` | int (10-3600) | 60 | Seconds between Carrier cloud syncs. | Unchanged. |
| `log_level` | enum | `info` | `debug|info|warning|error`. | New. |
| ~~`serial_tty`~~ | — | — | — | **Removed.** |

### 10.2 HA integration config

Unchanged: one field, `host`, pointing at the add-on's base URL.

---

## 11. Persistence

Two concerns:

1. **State cache** — last known thermostat report. Persisted to SQLite so that immediately after add-on restart the northbound API can answer reads without waiting for the next thermostat POST. Single-row table keyed by thermostat serial.
2. **Pending writes** — mutations made via the API that haven't yet been picked up by the thermostat. Persisted to SQLite so that an add-on restart doesn't lose a user's setpoint change. On startup, the scheduler re-arms any pending writes.

No historical data is retained. Time-series metrics, if ever needed, belong in Prometheus / InfluxDB external to the proxy.

---

## 12. Testing strategy

1. **Contract tests** — `schemathesis` runs the OpenAPI spec against the live service; any 500 on a valid input is a failure.
2. **Protocol replay** — capture a suite of real thermostat POSTs (XML) from a development device, replay against the southbound handler, assert the response XML matches byte-for-byte (modulo timestamp fields).
3. **Golden fixtures** — store representative `systems.json` / `status.json` dumps from the legacy proxy; assert the new `GET /v1/state` produces the semantic equivalent.
4. **HA integration integration test** — existing integration's test suite runs against a `pytest-asyncio`-spun-up proxy.

---

## 13. Migration plan

Phases, each shippable independently:

1. **Phase 0 — Freeze legacy, tag final release** on the existing Perl proxy. (Done: v1.0.x is the reference.)
2. **Phase 1 — OpenAPI spec finalized.** (This branch.) Design doc + `openapi.yaml` merged to `main` behind a clear note that no runtime changes have happened.
3. **Phase 2 — New add-on scaffolding.** Directory `addon/` (or `proxy/`) with FastAPI app, southbound stubs, generated Pydantic models. Runs but only serves `/v1/healthz` and canned `/v1/state`.
4. **Phase 3 — Southbound re-implementation.** Thermostat can point at the new add-on and it behaves correctly. Feature-gated behind an opt-in option.
5. **Phase 4 — Northbound write endpoints.** Holds, setpoints, activities, schedules all functional.
6. **Phase 5 — HA integration cutover.** A single PR updates the Python coordinator to the new API. Bump major version of the integration. Old add-on is deprecated in the README.
7. **Phase 6 — SSE push.** Opportunistic; coordinator keeps polling as a fallback.
8. **Phase 7 — Legacy add-on removed.** After a deprecation window (~2 releases), the Perl add-on is removed from the repo.

No dual-stack period is planned; the HA integration tracks the API version it knows.

---

## 14. Risks & open questions

| # | Risk / question | Notes |
|---|---|---|
| 1 | **Carrier's XML protocol is undocumented.** We depend entirely on upstream Infinitude's reverse engineering. | Mitigation: port the upstream Perl handlers 1:1 to Python in Phase 3, don't try to "clean up" the XML handling. |
| 2 | **Passthrough to Carrier cloud may involve TLS pinning or custom certificates.** | Need to inspect upstream `pass_reqs` code path before Phase 3. Assume TLS is standard until proven otherwise. |
| 3 | **Thermostat firmware variability.** Different Infinity/Evolution firmware versions may send slightly different XML. | Mitigation: protocol replay tests using captures from multiple firmware versions. Ask community for captures in Phase 3. |
| 4 | **HA add-on restart** briefly drops the thermostat's HTTP connection. | Acceptable: the thermostat retries. Document the expected ~30s post-restart gap. |
| 5 | **SSE over HA ingress** may not work with all reverse proxies. | Fall back to polling is always available. |
| 6 | **Hold `until`: "forever" vs. omitted** | Normalize in the API: `until: null` = indefinite, `until: "HH:MM"` = timed. Whole-house and zone holds behave the same. |
| 7 | **`activity: "manual"` asymmetry** | Today, whole-house hold forbids `manual`. Clarified in OpenAPI enum: `system.hold.activity` enum omits `manual`. |
| 8 | **Thermostat serial number** | Currently surfaced via `systems.json`; the new API exposes it under `GET /v1/system`. |

---

## 15. Out-of-scope, but worth noting

- **Multi-user auth / RBAC** — not needed; the add-on runs on a trusted LAN and HA ingress handles auth.
- **GraphQL** — rejected. The domain is small and stable; REST + SSE is the right shape.
- **WebSockets** — considered and rejected. SSE is simpler, proxy-friendly, and fits the unidirectional server→client push pattern.
- **CLI tool** — could ship a thin `curl`-equivalent later, not in v2.0.

---

## 16. Open to discussion

Before Phase 2 starts, please confirm or redirect:

1. **Repo layout.** Proposal: new top-level `addon/` directory (Python source + Dockerfile), legacy `infinitude/` stays until removed in Phase 7. Alternative: rename `infinitude/` to `infinitude-legacy/` now and use `infinitude/` for the new add-on.
2. **API versioning.** Proposal: path-based (`/v1/`). Alternative: header-based. Path-based is simpler and matches HA conventions.
3. **Hold `until` semantics.** Proposal: ISO-like `HH:MM` (24h local time, same as today) or `null` for indefinite. Alternative: pass an ISO 8601 datetime and let the server convert. `HH:MM` is what the thermostat natively uses, so we match.
4. **Schedule PUT atomicity.** Proposal: `PUT /v1/zones/{zoneId}/schedule` replaces the whole week in one call (what the HA integration does today). Alternative: `PUT /v1/zones/{zoneId}/schedule/days/{day}` per-day writes. Full-week PUT is simpler and matches the current flow; per-day is a future refinement if needed.
