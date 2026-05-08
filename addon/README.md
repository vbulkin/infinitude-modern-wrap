# Infinitude Modern Proxy (add-on)

Python/FastAPI rewrite of the legacy Perl Infinitude proxy. Southbound
handler, northbound write endpoints, persistent pending-write replay,
spec-shape SSE events, HA integration cutover with SSE consumer, and
full-Perl-parity Carrier cloud passthrough are all live.

See [`design/DESIGN.md`](../design/DESIGN.md) for architecture and
[`design/openapi.yaml`](../design/openapi.yaml) for the full API contract.

## Status

| Phase | Component | State |
|---|---|---|
| 2 | FastAPI scaffold + healthz/version | ✅ shipped |
| 3 | Southbound thermostat XML handler | ✅ shipped |
| 3 | SQLite persistence (state cache + pending writes) | ✅ shipped |
| 4 | Northbound write endpoints | ✅ shipped (all surfaces) |
| 4 | Spec-shape SSE (state.snapshot / state.update / hold.changed / notifications.received / health.changed) | ✅ shipped |
| 5 | HA integration cutover to the new API | ✅ shipped |
| 5 | HA-side SSE consumer with reconnect + `Last-Event-ID` resume | ✅ shipped (alpha.30) |
| 5 | Conditional polling (off while SSE up; resumes on disconnect) | ✅ shipped (alpha.31) |
| 6 | Legacy Mojolicious HTML UI (humidity / vacation / service reminders) | ⛔ obsolete; user-facing surfaces are now the HACS integration's Lovelace cards. The Python add-on does not serve `infinitude-ui.html`. |
| 7 | Carrier cloud passthrough — explicit forward proxy | ✅ shipped (alpha.24) |
| 7 | Carrier cloud passthrough — implicit bridge (status mirror, pull-through on `serverHasChanges`, directive pass-through) | ✅ shipped (alpha.25–55) |
| 7 | Vacation HA-side surface | ✅ shipped (alpha.46) |

> **Propagation behavior — read this first.** HA mutations propagate
> to the thermostat in seconds and to the Carrier app on the
> thermostat's own re-sync schedule (hours, sometimes). See
> [`design/LIMITATIONS.md`](../design/LIMITATIONS.md) for the empirical
> evidence behind this asymmetry and what the addon can / cannot do.

## API surface

### Health & meta

- `GET /v1/healthz` — component-scoped roll-up with thermostat staleness, state-store zones tracked, pending-write age, SSE subscriber count.
- `GET /v1/version` — proxy version, api version, commit SHA, build time.
- `GET /v1/config` — effective `carrier_bridge` (bool, alpha.48 — replaces the prior numeric `pass_reqs`) and `log_level` options.

### State (read)

- `GET /v1/state` — full State projection (system + all zones, overlay of config + latest telemetry).
- `GET /v1/system` — system-level projection (mode, hold, outdoor/humidifier, serial).
- `GET /v1/system/idu` — indoor unit config.
- `GET /v1/system/odu` — outdoor unit config.
- `GET /v1/system/vacation` — vacation window + setpoints + fan.
- `GET /v1/system/humidity` — per-mode humidity targets.
- `GET /v1/system/service` — service-reminder intervals/flags + life-remaining % for filter/UV/humidifier/ventilator.
- `GET /v1/system/energy` — per-mode runtime hours (cooling/hpheat/eheat/gas/reheat/fangas/fan/looppump) across six rolling periods (today / yesterday / this+last month / this+last year), plus SEER/HSPF efficiency ratings and per-mode display+enabled flags. Sourced from the thermostat's `/energy` POST (~daily cadence).
- `GET /v1/system/events` — equipment fault history (code, source, description, first-occurrence timestamp, occurrence count, active flag). Sourced from the thermostat's `/equipment_events` POST.
- `GET /v1/system/odu_status` — outdoor-unit live runtime: compressor stage (`Stage 0/1/2`) + parsed `operatingStage` integer, compressor RPM, suction/discharge refrigerant pressures + temperatures + superheat, expansion-valve position, blower RPM, static pressure, OAT, lockout state. Idle-state fields are null. Sourced from the thermostat's `/odu_status` POST (every few minutes when running).
- `GET /v1/system/idu_status` — indoor-unit live runtime: blower RPM, airflow CFM, static pressure, coil temperature, inducer RPM (gas furnaces), lockout state.
- `GET /v1/zones` — all zones (including disabled). Each zone carries a `conditioningStage` field (1, 2, or null) derived from the thermostat's `<zoneconditioning>` text — surfaces multi-stage HP/AC capacity stage without re-parsing strings.
- `GET /v1/zones/{id}` — single zone.
- `GET /v1/zones/{id}/activities` — all activities for a zone.
- `GET /v1/zones/{id}/activities/{id}` — single activity.
- `GET /v1/zones/{id}/schedule` — 7-day program.

### State (write)

- `PATCH /v1/system` — system mode.
- `PATCH /v1/system/vacation` — sparse update: active / start / end / setpoints / fan.
- `PATCH /v1/system/humidity` — sparse per-mode target RH.
- `PUT /v1/system/hold` / `DELETE /v1/system/hold` — whole-house hold.
- `PATCH /v1/zones/{id}` — manual activity setpoints (+ optional engage-hold).
- `PATCH /v1/zones/{id}/activities/{id}` — edit a named activity's heat/cool/fan without engaging a hold.
- `PUT /v1/zones/{id}/hold` / `DELETE /v1/zones/{id}/hold` — per-zone hold.
- `PUT /v1/zones/{id}/schedule` — full 7-day program overwrite.

### Events

- `GET /v1/events` — SSE stream of `state.snapshot` / `state.update` / `hold.changed` / `notifications.received` / `health.changed`. Clients resume with `Last-Event-ID`; ring-buffered, re-seeds with snapshot on gap. Keepalive comment every 15 s doubles as half-open-TCP probe.
- `GET /v1/notifications` — REST-backed ring buffer of raw thermostat notifications. Same arrivals also fire `notifications.received` on the SSE stream so live consumers see them in ~1 s.

### Carrier cloud relay

- **Forward proxy** (catch-all): `GET/POST/PUT/PATCH /http%3A//host/...` — URL-encoded explicit forward. Allowlist-gated against `*.carrier.com` / `*.bryant.com`. Used by the thermostat for firmware OTA (`/http%3A//www.ota.ing.carrier.com/releaseNotes/...`).
- **Implicit bridge**: every thermostat-bound POST (`/systems/{serial}/status`, `/notifications`, `/idu_config`, `/odu_config`, fallback metadata) is mirrored to `https://www.api.ing.carrier.com/...` (no per-call throttle — Carrier's pingRate signal handles device-side rate-limiting natively). Non-status mirrors fire-and-forget so a slow Carrier never makes the thermostat wait. Single boolean `carrier_bridge` (default `true`) toggles the entire bridge off for offline-first deployments.
- **Pull-through on `serverHasChanges`** — when Carrier responds to a status mirror with `serverHasChanges=true`, the bridge latches a flag; the next thermostat `/systems/{serial}/config` GET is relayed upstream (using the thermostat's own fresh OAuth signature — the only auth Carrier accepts), Carrier's tree is merged into local state, and the merged tree is served back. This is the **only** mechanism by which Carrier-app changes reach HA — see [`design/LIMITATIONS.md`](../design/LIMITATIONS.md) for why we can't push.
- **Directive pass-through** — when no local mutations are pending, the thermostat's status response IS Carrier's directive (Carrier's `pingRate` forwarded verbatim — pre-alpha.48 we forced 12 s and defeated Carrier's authoritative rate-limit). This is what surfaces Carrier's `serverHasChanges=true` so the thermostat actually fetches config.
- **Per-request access log** at INFO: `relay POST https://www.api.ing.carrier.com/systems/.../status -> 200 (143ms, 287 B)` mirrors uvicorn's access-log shape so outbound traffic sits alongside inbound in the same log stream.
- **Resilience**: 3 s outbound timeout + circuit breaker (opens after 3 consecutive failures; exponential cooldown to 5 min cap). Thermostat-facing endpoints stay sub-second when Carrier is unreachable.

### Debug

- `GET/POST/DELETE /v1/debug/capture[/start|/stop|/entries]` — flip a SQLite capture middleware on/off; tee inbound (southbound + northbound) and outbound (`carrier_out`) traffic with bodies for forensic inspection.

### Southbound (thermostat ↔ proxy)

The thermostat's existing XML endpoints are terminated internally and shape the northbound state:

- `POST /systems/{serial}` — boot config.
- `POST /systems/{serial}/status` — telemetry tick (~90 s).
- `POST /systems/{serial}/notifications` — event/alert push.
- `POST /systems/{serial}/idu_config` / `/odu_config` — equipment descriptors.
- `GET  /systems/{serial}/config` — thermostat pulls the latest (mutated) tree. Pending writes clear pull-observed here.

Write model: northbound PATCHes edit the retained `<config>` tree in place, enqueue a typed `pending_writes` row, and flip the `config_dirty` flag. The next status-POST directive signals `configHasChanges=true`; the thermostat then issues `GET /config` and we serve the mutated bytes. Pending rows are marked applied on that GET. See [`design/DESIGN.md`](../design/DESIGN.md) §4.3 / §4.4.2.

Replay: if the proxy restarts or the thermostat reboots with stale state, unapplied pending rows are re-applied onto the incoming config tree via `REPLAY_REGISTRY` before we persist it, so nothing the user wrote is lost. Pull-through from Carrier (`serverHasChanges` path) goes through the same replay so a concurrent HA mutation isn't reverted by Carrier's stale view.

## Local development

```bash
cd addon
pip install -e '.[dev]'
uvicorn infinitude_proxy.main:app --reload --port 3001
# then: open http://localhost:3001/docs for the live OpenAPI UI
```

## Running tests

```bash
cd addon
pytest
```

Current coverage: 367 tests across parser, mutations, state store, persistence, southbound handler, error shape, every northbound endpoint, SSE publisher/resume, ForwardProxy + CarrierBridge full-roundtrip + capture integration, heat-pump-install regression fixtures, energy + equipment-events parsing + multi-stage compressor surfacing, ODU/IDU live-status with `na`/`invalid` placeholder coercion.

## HA add-on build (local)

```bash
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest -t infinitude-modern .
docker run --rm -p 3001:3001 infinitude-modern
```
