# Infinitude Direct

This repository contains two components for controlling Carrier/Bryant Infinity thermostats through Home Assistant.

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
| **Custom Lovelace Card** (`src/infinitude-hvac-card.js`) | LitElement card with three tabs: Zones, Schedule, and Profiles. Bundled with esbuild. |

> **Dependency:** The HACS integration requires the Infinitude proxy to be running and accessible. Install the add-on above first (or run Infinitude separately), then point the integration to the proxy URL during setup.

## Features

### Climate Entities (per zone)
- Current temperature and humidity
- HVAC modes: Off, Heat, Cool, Heat/Cool (Auto)
- Preset modes: Home, Away, Sleep, Wake
- Target temperature and temperature range support
- Per-zone hold with activity selection and timer
- Extra attributes: damper position, fan mode, outdoor temperature, hold status

### Custom Lovelace Card
- **Zones tab** — Live zone cards with temps, humidity, conditioning status, and inline hold set/cancel with optimistic temperature display (debounced 800ms commits, pulsing amber indicator)
- **Schedule tab** — Visual weekly schedule editor per zone with drag-to-reorder periods, activity/time selectors, and save-to-thermostat
- **Profiles tab** — Edit heat/cool setpoints and fan speed per activity per zone
- **Whole-house hold** — Inline header picker for home/away/sleep/wake with apply/cancel
- Auto-discovers entities via the HA entity registry (no manual entity configuration)

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

Pushes to remote with tags.

```bash
npm run gh-release
```

Creates a GitHub Release with auto-generated notes (run separately after push).

### Version Management

Versions are managed automatically via git hooks:
- **Pre-commit** — Bumps the patch version in `manifest.json`, `config.yaml`, `infinitude-ui.html`, and `src/infinitude-hvac-card.js`, then runs the esbuild build and stages the output.
- **Post-commit** — Creates an annotated git tag `v{version}` from the manifest version.

## License

This project is licensed under the [MIT License](LICENSE).
