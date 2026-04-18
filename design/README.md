# Design — OpenAPI-first Infinitude rewrite

Planning artifacts for replacing the Perl Infinitude proxy with a Python/FastAPI add-on
that exposes a typed, OpenAPI-described northbound API. **No runtime changes yet.**

- [`DESIGN.md`](./DESIGN.md) — architecture, data flow, migration plan, open questions.
- [`openapi.yaml`](./openapi.yaml) — full API spec (OpenAPI 3.1).

## Quick facts

- Thermostat-facing protocol and Carrier cloud passthrough: **preserved 100%**.
- RS485 / `serial_tty`: **dropped**.
- Legacy `/native.html` Perl UI: **dropped**; the modern HTML UI becomes the only UI.
- `/v1/healthz` surfaces thermostat freshness, Carrier connectivity, state-store pressure, API uptime.
- Live updates via SSE at `/v1/events`; polling `/v1/state` remains supported.

## Reviewing the spec

Render locally with any OpenAPI viewer, e.g.:

```bash
npx @redocly/cli preview-docs design/openapi.yaml
```

or paste `openapi.yaml` into https://editor.swagger.io (local clipboard only — no upload).
