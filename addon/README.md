# Infinitude Modern Proxy (add-on)

Python/FastAPI rewrite of the legacy Perl Infinitude proxy. Southbound
handler, northbound write endpoints, persistent pending-write replay,
and spec-shape SSE events are all live; the HA integration + legacy
HTML UI cutover is the remaining track.

See [`design/DESIGN.md`](../design/DESIGN.md) for architecture and
migration plan, and [`design/openapi.yaml`](../design/openapi.yaml) for
the full API contract.

## Status

| Phase | Component | State |
|---|---|---|
| 2 | FastAPI scaffold + healthz/version | ✅ shipped |
| 3 | Southbound thermostat XML handler | ✅ shipped |
| 3 | SQLite persistence (state cache + pending writes) | ✅ shipped |
| 4 | Northbound write endpoints | ✅ shipped (all surfaces) |
| 4 | Spec-shape SSE (state.snapshot / state.update / hold.changed) | ✅ shipped |
| 5 | HA integration cutover to the new API | ⏳ post-cutover |
| 6 | Legacy HTML UI updates (humidity / vacation / service reminders) | ⏳ post-cutover |
| 7 | Carrier cloud passthrough (`pass_reqs`) | ⏳ not started |

## API surface

### Health & meta

- `GET /v1/healthz` — component-scoped roll-up with thermostat staleness, state-store zones tracked, pending-write age, SSE subscriber count.
- `GET /v1/version` — proxy version, api version, commit SHA, build time.
- `GET /v1/config` — effective `pass_reqs` and `log_level` options.

### State (read)

- `GET /v1/state` — full State projection (system + all zones, overlay of config + latest telemetry).
- `GET /v1/system` — system-level projection (mode, hold, outdoor/humidifier, serial).
- `GET /v1/system/idu` — indoor unit config.
- `GET /v1/system/odu` — outdoor unit config.
- `GET /v1/system/vacation` — vacation window + setpoints + fan.
- `GET /v1/system/humidity` — per-mode humidity targets.
- `GET /v1/system/service` — service-reminder intervals/flags + life-remaining % for filter/UV/humidifier/ventilator.
- `GET /v1/zones` — all zones (including disabled).
- `GET /v1/zones/{id}` — single zone.
- `GET /v1/zones/{id}/activities` — all activities for a zone.
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

- `GET /v1/events` — SSE stream of `state.snapshot` / `state.update` / `hold.changed`. Clients resume with `Last-Event-ID`; ring-buffered, re-seeds with snapshot on gap.
- `GET /v1/notifications` — REST-backed ring buffer of raw thermostat notifications (not on SSE — out of spec enum).

### Southbound (thermostat ↔ proxy)

The thermostat's existing XML endpoints are terminated internally and shape the northbound state:

- `POST /systems/{serial}` — boot config.
- `POST /systems/{serial}/status` — telemetry tick (~90 s).
- `POST /systems/{serial}/notifications` — event/alert push.
- `POST /systems/{serial}/idu_config` / `/odu_config` — equipment descriptors.
- `GET  /systems/{serial}/config` — thermostat pulls the latest (mutated) tree. Pending writes clear pull-observed here.

Write model: northbound PATCHes edit the retained `<config>` tree in place, enqueue a typed `pending_writes` row, and flip the `config_dirty` flag. The next status-POST directive signals `configHasChanges=true`; the thermostat then issues `GET /config` and we serve the mutated bytes. Pending rows are marked applied on that GET. See [`design/DESIGN.md`](../design/DESIGN.md) §4.3 / §4.4.2.

Replay: if the proxy restarts or the thermostat reboots with stale state, pending rows are re-applied onto the incoming config tree via `REPLAY_REGISTRY` before we persist it, so nothing the user wrote is lost.

## Local development

```bash
cd addon
pip install -e '.[dev]'
uvicorn infinitude_proxy.main:app --reload --port 3000
# then: open http://localhost:3000/docs for the live OpenAPI UI
```

## Running tests

```bash
cd addon
pytest
```

Current coverage: 224 tests across parser, mutations, state store, persistence, southbound handler, error shape, and every northbound endpoint including SSE publisher/resume semantics.

## HA add-on build (local)

```bash
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest -t infinitude-modern .
docker run --rm -p 3000:3000 infinitude-modern
```
