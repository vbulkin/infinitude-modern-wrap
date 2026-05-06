# Logging policy

Scope: the `infinitude_proxy.*` logger tree (addon side) and
`custom_components.infinitude_direct.*` (HA-integration side). Uvicorn's
access/error loggers are left with their own config.

## Levels

| Level   | Use for                                                                 |
|---------|-------------------------------------------------------------------------|
| DEBUG   | Per-request wire detail (body sizes, parsed counts), SSE event flow on consumer side, bridge skip reasons (cache hit / local-changes-pending). Off by default. |
| INFO    | Thermostat lifecycle (first telemetry, config received), notification arrivals with summary, northbound edits applied, SSE consumer connect/disconnect, outbound Carrier relay access lines, parsed enum-coercion fallbacks. |
| WARNING | Recoverable anomalies: missing/malformed fields the parser fell back on, SSE consumer reconnect attempts, Carrier relay network errors (forwarded transparently to thermostat), forbidden-host SSRF guard fires. |
| ERROR   | Per-request failures that produce non-2xx responses.                    |

## Conventions

- `logger = logging.getLogger(__name__)` at module top in any file that logs.
- Lazy `%s` formatting in log calls — never f-strings. Formatting only happens when the record is actually emitted.
- Request-handler logs always include `serial=` and the handler/path name so grep across a multi-unit deployment is trivial.
- Hot paths (parser, state_store reads) log only at WARNING+.
- Do not log full request/response bodies. Log sizes/counts and content-type. (DEBUG SSE-event log truncates `data` to 200 chars; bridge / forward-proxy access logs include byte count + duration.)

## Wire-up

`main._configure_logging()` reads `settings.log_level` and configures the
`infinitude_proxy` logger with a single StreamHandler. It is idempotent
(safe across test app instances) and does not touch the root logger.

The HA integration's logger (`custom_components.infinitude_direct.*`) follows HA's normal logging configuration — set per-logger levels via Settings → System → Logs or `configuration.yaml`'s `logger:` block.

## Known log sites

### Addon (`infinitude_proxy.*`)

- `southbound.post_metadata_fallback` — INFO per unhandled subpath hit.
- `state_store.append_notifications` — INFO per notification batch with `serial=… count=N first=<class>`; WARNING when an SSE subscriber's queue is full (event dropped for that subscriber).
- `state_store.apply_telemetry` — INFO on first telemetry / config received.
- `forward_proxy.ForwardProxy.forward` — INFO per request: `forward GET http://host/path -> 200 (Nms, B)`. WARNING on 504/502/403.
- `carrier_bridge.CarrierBridge.relay` — INFO per request: `relay POST https://host/path -> 200 (Nms, B)`. INFO on `opened carrier_changes window (120s) on serverHasChanges=true`. WARNING on relay error (transparent to thermostat). DEBUG per `skip` reason (cache hit / local-changes-pending / disabled / window-open).
- `parser._coerce_hvac_mode` — INFO on unknown HVAC mode coerced to OFF (heat-pump operational modes that the strict enum hadn't catalogued).
- `southbound.get_system_config` — INFO on `serving Carrier config to thermostat (window consumed, scheduled changes 60s)`.

### HA integration (`custom_components.infinitude_direct.*`)

- `coordinator._sse_loop` — INFO on `SSE: connected (resume id=…)` + `SSE: disconnected; resume Ns poll heartbeat`. WARNING on each reconnect attempt with backoff.
- `coordinator._handle_sse_event` — DEBUG per event: `SSE event: <type> id=<n> data=<first 200 chars>`.
- `coordinator.async_set_mode` etc. — no per-call log; the addon side records the resulting writes.

This file is the index — new sites land here as they ship.
