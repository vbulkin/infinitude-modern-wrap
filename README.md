# Infinitude Direct

This repository contains two components for controlling Carrier Infinity/Bryant Evolution thermostats through Home Assistant.

## What's Included

### 1. Home Assistant Add-on — Infinitude Proxy (`infinitude/`)

A Home Assistant add-on (app) that runs the [Infinitude](https://github.com/nebulous/infinitude) reverse-proxy inside HA. Carrier/Bryant Infinity thermostats must be configured to point to this proxy instead of the Carrier cloud, allowing local control and data access.

Built on the [`nebulous/infinitude`](https://hub.docker.com/r/nebulous/infinitude) Docker image ([source](https://github.com/nebulous/infinitude)).

The add-on includes a built-in web UI (`infinitude-ui.html`) for full thermostat management: per-zone temperature control, hold management, weekly schedule editing, and comfort profile configuration.

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
| `custom:infinitude-hvac-card` | **Composite tabbed dashboard** — Status, Zones, Schedule, Profiles in a single card. |
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

### Select Entity
- Whole-house hold activity selector (off / home / away / sleep / wake)

### Services
- `infinitude_direct.save_schedule` — Save a full weekly schedule for a zone
- `infinitude_direct.set_profile` — Set heat/cool setpoints and fan for a zone activity
- `infinitude_direct.cancel_hold` — Cancel an active hold for a zone
- `infinitude_direct.set_hold` — Set a hold for a zone with activity and optional duration
- `infinitude_direct.set_whole_house_hold` — Set a whole-house hold with activity and optional duration
- `infinitude_direct.cancel_whole_house_hold` — Cancel an active whole-house hold

### Auto-provisioned Frontend
- Card JS is copied to `/local/community/infinitude_direct/` and registered as a Lovelace resource with cache-busting (`?v={version}`)
- An **HVAC** dashboard is created in the sidebar automatically on first setup
- All frontend assets are cleaned up on integration removal

## Installation

### Add-on (Infinitude Proxy)

1. Add this repository to your Home Assistant Add-on Store.
2. Install the **Infinitude Direct** add-on.
3. Configure your thermostat's `pass_reqs` interval and optional `serial_tty` in the add-on settings.
4. Start the add-on — the proxy will be available on port 3000.

### Integration (HACS)

1. Add this repository as a custom repository in [HACS](https://hacs.xyz/).
2. Install **Infinitude Direct**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for **Infinitude Direct**.
5. Enter the Infinitude proxy URL (default: `http://local-infinitude:3000`).
6. The custom card, Lovelace resource, and HVAC dashboard are created automatically.

## Configuration

The integration is configured entirely through the UI. During setup you provide the Infinitude proxy host URL. The integration validates the connection by querying the `/status.json` endpoint.

### Add-on Options

| Option | Type | Default | Description |
|---|---|---|---|
| `pass_reqs` | int | 60 | Seconds between thermostat pass-through requests |
| `serial_tty` | string | `""` | Serial device path (leave empty for network-only) |

## Architecture

```
Thermostat <──> Infinitude Proxy (Add-on) <──> HA Integration
                     :3000                    (local polling)
```

The integration polls `systems.json` and `status.json` from the Infinitude proxy every 30 seconds and parses zone data including temperatures, setpoints, activity schedules, and conditioning state.

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

- **Pre-commit hook** — Bumps the patch version in `manifest.json`, `config.yaml`, `infinitude-ui.html`, and `src/infinitude-hvac-card.js`, rebuilds the card via esbuild, and stages everything.
- **Post-commit hook** — Creates an annotated git tag `v{version}` from the manifest version.
- **`npm run release`** — Pushes commits and tags to remote.
- **`npm run gh-release`** — Creates a GitHub Release with auto-generated notes (manual, separate step).

## License

This project is licensed under the [MIT License](LICENSE).
