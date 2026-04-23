# Logging policy

Scope: the `infinitude_proxy.*` logger tree. Uvicorn's access/error
loggers are left with their own config.

## Levels

| Level   | Use for                                                                 |
|---------|-------------------------------------------------------------------------|
| DEBUG   | Per-request wire detail (body sizes, parsed counts). Off by default.    |
| INFO    | Thermostat lifecycle: first telemetry, config received, unhandled metadata subpath, northbound edits applied. |
| WARNING | Recoverable anomalies: missing/malformed fields the parser fell back on, directive flag set but never acked. |
| ERROR   | Per-request failures that produce non-2xx responses.                    |

## Conventions

- `logger = logging.getLogger(__name__)` at module top in any file that logs.
- Lazy `%s` formatting in log calls — never f-strings. Formatting only happens when the record is actually emitted.
- Request-handler logs always include `serial=` and the handler/path name so grep across a multi-unit deployment is trivial.
- Hot paths (parser, state_store reads) log only at WARNING+.
- Do not log request/response bodies. Log sizes and counts instead.

## Wire-up

`main._configure_logging()` reads `settings.log_level` and configures the
`infinitude_proxy` logger with a single StreamHandler. It is idempotent
(safe across test app instances) and does not touch the root logger.

## Known log sites today

- `southbound.post_metadata_fallback` — INFO per unhandled subpath hit.
- `state_store.append_notifications` — WARNING when an SSE subscriber's queue is full (event dropped for that subscriber; others unaffected).

Future sites land here as the list grows so this file stays the index.
