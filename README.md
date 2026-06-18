# Infinitude Direct

This repository contains two components for controlling Carrier Infinity/Bryant Evolution thermostats through Home Assistant.

## What's Included

### 1. Home Assistant Add-on — Infinitude Modern Proxy (`addon/`)

A Home Assistant add-on (app) running a Python/FastAPI reverse-proxy for Carrier/Bryant Infinity thermostats. The thermostat is DNS-redirected at the LAN layer to this proxy instead of the Carrier cloud, enabling local control plus optional pass-through to Carrier (firmware updates, MyInfinity-app round-trips), and a typed OpenAPI northbound API that the HACS integration below consumes.

Ships as `Infinitude Modern Proxy` in the add-on store, binds port **3001**, and exposes:

- `/v1/*` typed JSON API (state read, mutations, healthz, debug capture)
- `/v1/events` SSE stream of `state.snapshot` / `state.update` / `hold.changed` / `notifications.received` / `health.changed` with `Last-Event-ID` resume
- `/systems/{serial}/...` thermostat-facing southbound endpoints (Carrier wire shape preserved)
- Catch-all forward proxy for `/http%3A//host/...` URL-encoded requests (firmware OTA)
- Implicit Carrier-cloud bridge: per-tick status mirror, proactive config pull-through when Carrier signals `serverHasChanges`, fire-and-forget mirrors for thermostat POSTs, and a circuit breaker that backs off during Carrier outages

OpenAPI spec lives at [`design/openapi.yaml`](design/openapi.yaml). Source lives under [`addon/`](addon/).

### 1b. Legacy Add-on — Infinitude Direct (`infinitude/`)

The prior Perl/Mojolicious add-on (built on [`nebulous/infinitude`](https://github.com/nebulous/infinitude)) is still in the repo under [`infinitude/`](infinitude/) as a rollback target during the cutover window ([design/CUTOVER.md](design/CUTOVER.md)). It binds port 3000. New installs should use the Modern Proxy above; the legacy add-on is scheduled for removal after two stable releases of the Python rewrite ([DESIGN.md §13 Phase 7](design/DESIGN.md#13-migration-plan)).

### 2. HACS Integration — Native HA Dashboard (`custom_components/infinitude_direct`)

A HACS-installable Home Assistant integration that provides a native HA dashboard for controlling your Carrier/Bryant Infinity thermostats. Features per-zone climate entities, hold management with activity and duration pickers, weekly schedule editing, and comfort profile configuration — all through a custom Lovelace card auto-installed in the sidebar.

| Component | Description |
|---|---|
| **Climate, Select & Sensor Platforms** | Per-zone climate entities, whole-house hold select, damper/fan/OAT/status sensors |
| **Custom Lovelace Cards** (`src/*.js`) | LitElement-based cards bundled with esbuild. Composite tabbed card plus standalone per-feature cards (zone, status, schedule, profiles). |

> **Dependency:** The HACS integration requires the Infinitude proxy to be running and accessible. Install the add-on above first (or run Infinitude separately), then point the integration to the proxy URL during setup.

## Features

### Climate Entities (per zone)
- Current temperature and humidity
- HVAC modes: Off, Heat, Cool, Heat/Cool (Auto), Fan Only
- HVAC actions: Heating, Cooling, Dehumidifying, Idle, Off
- Preset modes: Home, Away, Sleep, Wake, Manual
- Target temperature and temperature range support
- Per-zone hold with activity selection and timer
- Extra attributes: damper position, fan mode, outdoor temperature, hold status

### Custom Lovelace Cards

All cards extend a shared base with registry-driven auto-discovery, so no manual entity wiring is required (except for the single-zone card, which takes one entity).

| Card type | Description |
|---|---|
| `custom:infinitude-hvac-card` | **Composite tabbed dashboard** — Status, Schedule, Profiles tabs in a single card (per-zone rows render inside the Status tab). |
| `custom:infinitude-status-card` | System mode, outdoor temp, humidifier, connectivity, and whole-house hold row. |
| `custom:infinitude-zone-card` | Single zone (takes `entity: climate.xxx` in config). **Visual editor** with a dropdown filtered to Infinitude climate entities. |
| `custom:infinitude-schedule-card` | Weekly schedule editor per zone with activity/time selectors and save. |
| `custom:infinitude-profiles-card` | Heat/cool setpoints and fan speed per activity per zone. |

Features across cards:
- **Zone cards** — Live temp, humidity, conditioning status, inline hold set/cancel with optimistic temperature display (debounced 800ms commits, pulsing amber indicator)
- **Whole-house hold** — Header picker for home/away/sleep/wake with duration options
- **Circled zone numbering** (①②③…) matches the HTML UI so zones are visually consistent
- **Mobile-friendly** — schedule and profile rows tighten automatically below 520px viewport width

### Sensors
- Outdoor air temperature (OAT)
- System operating status
- Humidifier state
- Per-zone damper position and fan mode
- **Diagnostics** (alpha.37 — sourced from `/v1/system/odu_status` + `idu_status` + `energy` + `events`; report unavailable until the thermostat seeds each subpath):
  - Compressor stage (0/1/2), compressor RPM
  - Suction pressure, discharge temperature, outdoor coil temperature
  - Static pressure, indoor blower RPM, airflow (CFM)
  - Cooling efficiency (SEER), heating efficiency (HSPF) — install reference
  - Equipment events recorded (full history count, with up to 20 most-recent events as an attribute)

### Binary Sensor
- `binary_sensor.infinitude_fault_active` — `PROBLEM` device class, ON when any equipment event is currently asserted (`active=true`). Companion of the fault-count sensor; latest fault code/description/source/local-time exposed as attributes for templating.

### Select Entity
- Whole-house hold activity selector (off / home / away / sleep / wake)

### Services
- `infinitude_direct.save_schedule` — Save a full weekly schedule for a zone
- `infinitude_direct.set_profile` — Set heat/cool setpoints and fan for a zone activity
- `infinitude_direct.cancel_hold` — Cancel an active hold for a zone
- `infinitude_direct.set_hold` — Set a hold for a zone with activity and optional duration
- `infinitude_direct.set_whole_house_hold` — Set a whole-house hold with activity and optional duration
- `infinitude_direct.cancel_whole_house_hold` — Cancel an active whole-house hold
- `infinitude_direct.set_vacation` — Enter or update vacation mode (active/start/end/heat/cool/fan, sparse)
- `infinitude_direct.cancel_vacation` — Exit vacation mode (keeps the configured window)

### Auto-provisioned Frontend
- Card JS is copied to `/local/community/infinitude_direct/` and registered as a Lovelace resource with cache-busting (`?v={version}`)
- An **HVAC** dashboard is created in the sidebar automatically on first setup
- All frontend assets are cleaned up on integration removal

## Installation

### Add-on (Infinitude Modern Proxy)

1. Add this repository to your Home Assistant Add-on Store.
2. Install the **Infinitude Modern Proxy** add-on.
3. Configure `carrier_bridge` (Carrier passthrough on/off) and `log_level` in the add-on options.
4. Start the add-on — the proxy will be available on port **3001**, both on the LAN and through HA ingress.

See [design/CUTOVER.md](design/CUTOVER.md) for redirecting the thermostat to the proxy at the LAN layer.

### Integration (HACS)

1. Add this repository as a custom repository in [HACS](https://hacs.xyz/).
2. Install **Infinitude Direct**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for **Infinitude Direct**.
5. Enter the Infinitude proxy URL (default: `http://local-infinitude:3001`).
6. The custom card, Lovelace resource, and HVAC dashboard are created automatically.

## Configuration

The integration is configured entirely through the UI. During setup you provide the Infinitude Modern Proxy URL; the integration validates the connection by calling `/v1/healthz` on the proxy.

### Add-on Options

| Option | Type | Default | Description |
|---|---|---|---|
| `carrier_bridge` | bool | `true` | Whether the implicit Carrier-cloud bridge runs. Set to `false` for fully offline-first operation — the addon never reaches out to `api.ing.carrier.com` (MyInfinity-app round-trips disabled, Carrier-cloud dot stays grey). Replaced the numeric `pass_reqs` cadence in alpha.48: the proxy no longer throttles or caches Carrier traffic, since Carrier's own `pingRate` directive handles device-side rate-limiting. |
| `log_level` | enum | `info` | Proxy log verbosity (`debug` / `info` / `warning` / `error`). DEBUG surfaces per-SSE-event flow on the HA-integration side and bridge skip-reasons. |

## Architecture

```
                       ┌─────────── Carrier cloud ───────────┐
                       │  www.api.ing.carrier.com (mirror)   │
                       │  www.ota.ing.carrier.com (firmware) │
                       └──────────────▲──────────────────────┘
                                      │ httpx (CarrierBridge + ForwardProxy)
                                      │ allowlist-gated, circuit-breaker-guarded
                                      │
Thermostat ◀──xml──▶ Infinitude Modern Proxy (Add-on) ◀──HTTP+SSE──▶ HA Integration
                              :3001                      (event-driven)
```

**HA integration data flow:**

The HA coordinator subscribes to the addon's SSE stream on startup. Each `state.update` / `hold.changed` / `notifications.received` event triggers a debounced refresh from `/v1/state` — so panel-set holds, fault notifications, and current-temp drift propagate to HA in roughly one second.

While SSE is connected, scheduled polling is disabled (the addon's 15 s keepalive ping is the heartbeat). On SSE disconnect the coordinator immediately resumes a 60 s heartbeat poll until the consumer reconnects with backoff + `Last-Event-ID` resume — so missed events get replayed from the addon's ring buffer rather than dropped.

**Carrier cloud relay:**

Two paths handle thermostat → Carrier requests:
- **`ForwardProxy`** for explicit URL-encoded requests (`/http%3A//www.ota.ing.carrier.com/releaseNotes/…`) — firmware update checks. Allowlist-gated against `*.carrier.com` / `*.bryant.com`.
- **`CarrierBridge`** for implicit thermostat-bound traffic (`/systems/{serial}/status`, `/notifications`, `/idu_config`, `/odu_config`). Mirrors thermostat POSTs to Carrier on every tick — Carrier's own `pingRate` directive handles device-side rate-limiting, so the proxy no longer throttles or caches (the alpha.48 simplification that retired `pass_reqs`). When a relayed status response carries `serverHasChanges=true`, the bridge latches a pull so the thermostat's next `/config` GET is relayed upstream with the device's own auth and merged into the local tree. A circuit breaker (3 consecutive failures → 30 s–5 min exponential cooldown) keeps a sustained Carrier outage from paying a timeout on every call. Every Carrier-bound call routes through a single `_outbound` chokepoint so auth can't be bypassed.

Both directions land in the same SQLite `capture_traffic` table (when `/v1/debug/capture` is on) for symmetric forensic visibility.

## Development

### Prerequisites

- Node.js (for building the Lovelace card)
- npm

### Setup

```bash
npm install
```

### Build

```bash
npm run build
```

This bundles `src/infinitude-hvac-card.js` (with Lit) into a single minified file at `custom_components/infinitude_direct/www/infinitude-hvac-card.js` via esbuild.

### Release

```bash
npm run release
```

Pushes commits and tags to remote.

```bash
npm run gh-release
```

Creates a GitHub Release with auto-generated notes (run separately when desired).

### Version Management

The Python add-on and the HACS integration share a single version number; four files carry it:

- `addon/config.yaml` (canonical source)
- `addon/pyproject.toml`
- `custom_components/infinitude_direct/manifest.json`
- `src/shared.js` (Lovelace card banner)

Hooks and scripts:

- **Pre-commit hook** — On `main` only, and only for stable releases (no `-alpha.N` / `-beta.N` / `-rc.N` suffix), bumps the patch version in `addon/config.yaml`, `custom_components/infinitude_direct/manifest.json`, and `src/shared.js`; rebuilds the Lovelace card via `npm run build`; stages everything. Pre-release versions are bumped manually (including `addon/pyproject.toml`, which the hook does not touch).
- **Post-commit hook** — Creates an annotated git tag `v{version}` from the manifest version.
- **`npm run release`** — Pushes commits and tags to remote.
- **`npm run gh-release`** — Creates a GitHub Release with auto-generated notes (manual, separate step).

## License

This project is licensed under the [MIT License](LICENSE).
