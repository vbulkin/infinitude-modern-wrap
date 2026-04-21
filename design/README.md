# Design — OpenAPI-first Infinitude rewrite

Planning artifacts for replacing the Perl Infinitude proxy with a Python/FastAPI add-on
that exposes a typed, OpenAPI-described northbound API. The Python add-on is code-complete
as of Phase 4; Phase 5 (HA integration cutover) is next. See [`CUTOVER.md`](./CUTOVER.md)
for the operational plan.

- [`DESIGN.md`](./DESIGN.md) — architecture, data flow, migration plan, open questions.
- [`openapi.yaml`](./openapi.yaml) — full API spec (OpenAPI 3.1).
- [`CUTOVER.md`](./CUTOVER.md) — operational plan for swapping the deployed Perl add-on for the Python one.
- [`LOGGING.md`](./LOGGING.md) — log-level policy for the `infinitude_proxy.*` tree.

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
