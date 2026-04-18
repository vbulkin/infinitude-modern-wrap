# Infinitude Modern Proxy (add-on)

Python/FastAPI rewrite of the legacy Perl Infinitude proxy. **Phase 2 scaffold** — the
southbound thermostat protocol and Carrier passthrough are not yet implemented; only
the northbound HTTP API surface is live, returning canned data.

See [`design/DESIGN.md`](../design/DESIGN.md) for architecture and migration plan,
and [`design/openapi.yaml`](../design/openapi.yaml) for the full API contract.

## Phase 2 status

Implemented:

- `GET /v1/healthz` — returns a Pydantic-validated Health snapshot with canned component statuses.
- `GET /v1/version` — real build info (package version, api=v1, commit via env var).
- `GET /v1/state` — canned two-zone state snapshot, schema-compliant.
- `GET /v1/config` — reflects the `pass_reqs` and `log_level` options.

Not yet implemented (later phases):

- Southbound thermostat XML handler (Phase 3).
- Carrier cloud passthrough (Phase 3).
- Mutating northbound endpoints (Phase 4).
- SSE event stream (Phase 6).

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

## HA add-on build (local)

```bash
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest -t infinitude-modern .
docker run --rm -p 3000:3000 infinitude-modern
```
