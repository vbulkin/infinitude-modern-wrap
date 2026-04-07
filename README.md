# Infinitude Direct

> **⚠️ Pre-Alpha — This project is in early development and not yet ready for production use. Expect breaking changes, incomplete features, and rough edges.**

A Home Assistant integration and add-on for controlling Carrier/Bryant Infinity thermostats via [Infinitude](https://github.com/nebulous/infinitude).

The add-on is built on the [`nebulous/infinitude`](https://hub.docker.com/r/nebulous/infinitude) Docker image ([source](https://github.com/nebulous/infinitude)).

## What's Included

| Component | Description |
|---|---|
| **HACS Integration** (`custom_components/infinitude_direct`) | Climate platform that communicates with an Infinitude proxy to expose your thermostat zones in Home Assistant. |
| **HA Add-on** (`infinitude/`) | Packages the Infinitude proxy as a Home Assistant add-on with ingress support. |

## Features

- Multi-zone climate entities with current temperature and humidity
- HVAC modes: Off, Heat, Cool, Heat/Cool (Auto), Fan Only
- Preset modes: Home, Away, Sleep, Wake
- Target temperature and temperature range support
- Extra attributes: damper position, fan mode, outdoor temperature, hold status
- Config flow UI — no YAML configuration needed
- 30-second polling interval

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

This project is licensed under the [MIT License](LICENSE).
