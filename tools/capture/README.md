# Infinitude capture proxy

Tiny FastAPI proxy that sits between a Carrier/Bryant thermostat and an upstream
Infinitude instance. Every request and response is written to disk as a fixture;
traffic is forwarded transparently so the thermostat doesn't notice.

**Purpose:** collect real-world XML captures for the Phase 3 southbound protocol
replay tests in [../../addon/](../../addon/). Without these captures, the
southbound handler cannot be validated against a physical device.

## What it captures

Per request, three files in `./captures/`:

- `<ts>_<seq>_<METHOD>_<slug>.meta.json` — method, path, query, headers, status, timing.
- `<ts>_<seq>_<METHOD>_<slug>.request.{xml,json,bin}` — raw request body.
- `<ts>_<seq>_<METHOD>_<slug>.response.{xml,json,bin}` — raw response body.

## What it does NOT capture

Only the **thermostat ↔ Infinitude** leg. Carrier cloud passthrough traffic
originates from Infinitude outbound and does not flow through this proxy. If you
also want Carrier-side captures you need a second interception point on
Infinitude's upstream (a mitmproxy instance that Infinitude is configured to
route `api.ing.carrier.com` through, for example). That is a follow-up tool.

### Carrier-side response fixtures — already captured

Carrier's passthrough responses are cached verbatim by upstream Infinitude
(`$store->set("$nk.xml", $tx->res->body)` in the Perl source) and are reachable
via its own HTTP catchall — no proxy or filesystem access required. A curated
set has already been pulled from a live Infinitude, scrubbed, and committed
under [`../../addon/tests/fixtures/carrier/`](../../addon/tests/fixtures/carrier/):
`Alive.xml`, `api-config.json`, `energy.xml`, `manifest.xml`,
`notifications.xml`, `status.xml`, `systems.xml`, `time.xml`.

To refresh them, `curl http://<infinitude-host>:3000/<name>.xml` and re-scrub.
This capture proxy is only needed for the *request* bodies the thermostat
sends, which Infinitude parses and discards.

## Prerequisites

- Python 3.12+.
- The addon's venv, or any venv with `fastapi`, `httpx`, `uvicorn` installed:

  ```bash
  cd addon
  pip install -e '.[dev]'
  ```

## Running

From the repo root:

```bash
export CAPTURE_UPSTREAM=http://<legacy-infinitude-host>:3000
export CAPTURE_DIR=./captures
python tools/capture/proxy.py --port 3001
```

Defaults: binds `0.0.0.0:3001`, writes to `./captures/`.

## Inserting it in the traffic path

You have two options depending on how the thermostat currently reaches
Infinitude:

**DNS override (typical HA add-on setup).** Your thermostat resolves
`api.ing.carrier.com` (or similar) to the Infinitude host via router-level DNS.
To capture, either:
1. Change the DNS entry temporarily to point at the machine running this proxy,
   with `CAPTURE_UPSTREAM` set to the real Infinitude IP:port; or
2. Run this proxy on the same host as Infinitude on a different port, then
   update the DNS to point at `host:3001`.

**Direct IP config on the thermostat.** Reconfigure the thermostat's server
field to the capture proxy's IP:port, leave Infinitude's address in
`CAPTURE_UPSTREAM`.

In both cases, restore the original setting when you have enough captures
(~15–30 minutes should give you a representative sample of GET polls and one
or two telemetry POSTs).

## Sanity check

With the proxy running and traffic flowing, you should see stdout lines like:

```
[20260417T223045.123Z] #0001 POST /systems/1234A56789/status -> 200 (8432B req, 24B resp, 87ms)
[20260417T223112.001Z] #0002 GET /systems/1234A56789 -> 200 (0B req, 19244B resp, 42ms)
```

And `./captures/` filling up with paired `.request.xml` / `.response.xml` files.

## What to do with the captures

1. Eyeball a couple of `.response.xml` files — they should be well-formed XML.
2. **Scrub before committing.** Run [`../scrub/scrub_fixtures.py`](../scrub/scrub_fixtures.py)
   over the files to replace zone names with `Zone <id>`, absolute timestamps
   with a sentinel UTC, and serials with `0000TEST0000`:

   ```bash
   python tools/scrub/scrub_fixtures.py --dir addon/tests/fixtures/carrier
   ```

   Idempotent — running twice is a no-op. Structural XML is preserved so the
   fixtures remain representative.
3. Commit a curated subset under `addon/tests/fixtures/` (Phase 3).
4. The replay test harness will load meta + request body, call the southbound
   handler, and assert the produced response matches the captured one
   modulo timestamps.
