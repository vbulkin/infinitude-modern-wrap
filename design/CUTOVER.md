# Infinitude Proxy — Cutover Plan (Perl → Python)

Operational plan for replacing the legacy `infinitude/` (Perl/Mojolicious) add-on with the new `addon/` (Python/FastAPI) add-on in a deployed Home Assistant instance.

Companion to [`DESIGN.md`](./DESIGN.md) §13 (migration phases). This doc answers the question: *given the Python proxy is code-complete, what's the safe procedure to flip production traffic?*

## Scope

- **In scope:** switching a single HA host's thermostat from the Perl add-on to the Python add-on, including pre-cutover validation, rollback procedure, and post-cutover follow-ups.
- **Out of scope:** the HA integration and the Lovelace cards. Both are being developed in parallel on the same alpha train as the add-on and are not gated on cutover; when cutover lands, they're already there waiting for live data (see "Post-cutover sequencing" below for current status, and DESIGN.md §13 Phase 5/6 for long-term).

## Key facts driving the plan

- **Single thermostat, single HA host.** Not a fleet migration — no canary / percentage rollout.
- **Thermostat addressing is a built-in proxy setting.** The Carrier Infinity thermostat has a proxy host/port configured directly on the device (installer settings). It POSTs telemetry and GETs config from whatever IP:port is in that setting — no router port-forward, no iptables rule, no DNS override involved. Cutover is literally "change the port in the thermostat's proxy setting."
- **The two add-ons live on different ports and coexist.** As of add-on `2.0.0-alpha.5`, the Python add-on binds `3001` (container + host + ingress) and the legacy Perl add-on binds `3000`. Both can run simultaneously; only the thermostat's proxy setting decides which one it actually talks to. This replaces the earlier "swap what's bound to port 3000" plan.
- **Persistence is local.** The Python add-on's SQLite lives in `/data/` (HA add-on convention). A full rehydrate from scratch takes one `<config>` POST (≤ a few seconds after the first thermostat tick). No data migration from the Perl add-on is required or possible — shapes differ.
- **Cold-start is now a visible state.** As of alpha.8, `/v1/state` returns HTTP 503 (`error.code: upstream_unavailable`) until the first `<config>` POST arrives. Pre-alpha.8 returned demo/canned data; that is gone. Validation steps must account for the 503 window.
- **Carrier cloud passthrough is not yet implemented** in the Python proxy. Cutover with passthrough-dependent features (e.g. MyInfinity app → thermostat changes) will delay those commands by up to the next manual hard-refresh. See §"Open items" below.

## Prerequisites (must be green before cutover)

- [ ] **Full Python test suite green** (`pytest` in `addon/`). Current: 229 passing.
- [ ] **Schemathesis contract smoke** against a live Python add-on instance (openapi.yaml round-trip).
- [ ] **Boot-sequence replay** — the Perl add-on's captured thermostat boot POSTs (`boot_01..06`) drive the Python southbound handler without error; state projects to the expected shape on `GET /v1/state`.
- [ ] **Steady-state replay** — `telemetry_steady.xml` POSTed 10× in a row; state-store stays internally consistent, SSE emits one `state.update` per POST.
- [ ] **Write round-trip** — PATCH `/v1/zones/1` → `config_dirty=true` → directive signals → manual GET `/systems/{serial}/config` serves mutated XML → pending row clears. Covered by tests; re-verify against a live instance.
- [ ] **Restart replay** — kill/restart the add-on between a pending write and the thermostat's `GET /config`: on restart, the pending row survives, `apply_config` replays it onto the next thermostat POST, and the mutation is not lost.
- [ ] **Docker image builds clean** for all four HA architectures listed in `config.yaml` (`aarch64 / amd64 / armhf / armv7`).
- [ ] **Capture fixtures frozen** — `addon/tests/fixtures/thermostat/` contains one full boot sequence + one user-action telemetry delta + one notifications batch from the actual thermostat that's about to be cut over. Pull fresh captures if the on-device firmware has moved since the last snapshot.
- [ ] **`/v1/healthz` returns `status: healthy`** once live telemetry is flowing (stale threshold 300 s).
- [ ] **`/v1/state` returns 503 before first config POST**, and shape-correct JSON with non-null live fields after. Confirm the 503 envelope is `{"error": {"code": "upstream_unavailable", "message": "..."}}`.

## Pre-cutover: smoke check

Goal: prove the Python proxy is serving cleanly on `:3001` before anything is asked to talk to it over the wire.

Both add-ons are already bound to different ports (Perl `:3000`, Python `:3001`) and coexist on the same HA host. The Perl add-on continues to serve the live thermostat (if installed); the Python add-on is reachable but idle from the thermostat's point of view until its proxy setting is changed.

Protocol correctness against captured thermostat traffic is covered by the frozen fixtures under `addon/tests/fixtures/thermostat/` — boot sequence (`boot_01..06`), steady telemetry, and three user-action deltas (setpoint, opmode, schedule). The pytest suite (229 tests) replays these on every commit. The pre-cutover checklist below is about the *running add-on on the HA host*, not about re-deriving protocol coverage.

1. **Both add-ons installed and running.** Perl add-on on port 3000 continues to serve the live thermostat. Python add-on on port 3001 reachable at `http://<ha>:3001/` (landing page) and `http://<ha>:3001/v1/healthz` (200, `status: degraded` or `unknown` until first thermostat tick).
2. **Cold `/v1/state` returns 503.** Confirm `GET http://<ha>:3001/v1/state` returns HTTP 503 with `error.code: upstream_unavailable`. This confirms the cold-start path and that no stale demo data is being served.
3. **Replay one boot sequence manually.** POST `addon/tests/fixtures/thermostat/boot_01_system_config.xml` as `/systems/{serial}` (the full-config upload path — handler at `addon/src/infinitude_proxy/southbound.py:126`; note `/systems/{serial}/config` is `GET`-only) to `:3001`. The fixture's serial is `0000TEST0000`. Send the raw XML with `content-type: application/xml` (the test suite's convention — the live thermostat uses `application/x-www-form-urlencoded` but the handler accepts either). `/v1/state` should flip from 503 to a populated body with the fixture's zones.
4. **Observe SSE briefly.** After step 3, subscribe with `curl -N http://<ha>:3001/v1/events`; confirm `state.snapshot` on connect and `state.update` on a subsequent `PATCH /v1/zones/1` (simpler trigger than replaying `telemetry_steady.xml`, same SSE signal). Subscribing *before* step 3 should fail with 503, not open a stream. Run this from a shell on any host that can reach `:3001` — the HA MCP add-on API tool can't drive long-lived streams, so this step is the one part of the smoke check that doesn't automate via MCP.
5. **Hit one NB API mutation.** PATCH `/v1/zones/1` with a setpoint change. Confirm 200, and `/v1/state` reflects it. No thermostat is involved — this validates the write path end-to-end against the replay store.

Any failure here is a cutover blocker. Mirror-capture against the live thermostat's port-3000 traffic for multi-hour validation was planned in earlier drafts and is no longer required — the fixture suite supersedes it.

## Post-smoke-check cleanup

The smoke check seeds the state store with fixture data (`0000TEST0000`, synthetic zones, any PATCH holds set during step 5). That state persists to `/data/state.db` across add-on restarts. Before cutover, wipe it so the first POST from the real thermostat rehydrates cleanly and `/v1/state` returns the authentic serial / zones rather than a mix of fixture + real.

Easiest path in HA (no container shell needed):

1. **Uninstall the Modern Proxy add-on** (Settings → Add-ons → Infinitude Modern Proxy → ⋮ → Uninstall). This removes the add-on's `/data` volume entirely.
2. **Reinstall from the store** and re-enter `pass_reqs` / `log_level` in Configuration. The add-on slug is stable (`fda963a3_infinitude_modern`), so the ingress URL is unchanged.
3. **Start the add-on** and confirm `/v1/state` returns 503 `upstream_unavailable` again (`/v1/healthz` should be `degraded` with `zonesTracked: 0` and `thermostat.status: unreachable`).

Alternative: stop the add-on, delete `/addon_configs/fda963a3_infinitude_modern/state.db` via the File editor or SSH add-on, start it again. Same result, preserves options, but requires another add-on to reach the filesystem. Uninstall/reinstall is shorter when state.db is the only thing you need to clear.

## Cutover procedure

Once the smoke check and cleanup above pass. The add-on ports do **not** change — cutover changes one field in the thermostat's proxy setting.

1. **Announce downtime** to housemates: "thermostat proxy offline, ~2 min." In practice the thermostat continues to run locally; only the HA UI loses fresh data during the gap.
2. **Back up the Perl add-on's state** (skip if Perl add-on is not installed on this host — no state to back up). From the HA host: copy the legacy add-on's data directory to a safe location. Belt-and-suspenders — the Python add-on won't read it, but if rollback is needed this data is what the Perl add-on boots from.
3. **Confirm the Python add-on is running on `:3001`.** HA → Add-ons → Infinitude Modern Proxy → status is "Started", `/v1/healthz` returns 200 (`status: degraded` is fine pre-traffic — it flips to `healthy` on first thermostat tick).
4. **Change the thermostat's proxy port from `3000` to `3001`.** On the Infinity wall panel, go into installer settings → proxy/server configuration, change the port field from `3000` to `3001`. Keep the host IP the same (`192.168.1.233`). Save. The Perl add-on (if installed) stays running — it just stops receiving traffic.
5. **Watch the first thermostat tick.** Tail the Python add-on logs. Within ~90 s (one telemetry cadence) the thermostat will POST `/status`; logs should show parser success and state-store update. `/v1/state` flips from 503 to a populated body on the first `<config>` POST. Within the next few minutes the boot-shaped POSTs (`/config`, `/idu_config`, `/odu_config`, `/notifications`) will flow as part of steady-state operation or a forced reboot.
6. **Force a thermostat reboot** (at the wall panel or via a power-cycle) if step 5 doesn't produce a full boot sequence within 10 minutes — the state store rehydrates cleanly on boot and this reduces the post-cutover warm-up window.
7. **Validate.** Hit `/v1/healthz` — `thermostat.status` should be `healthy`. Confirm `/v1/state` shows accurate live values. Try one PATCH (e.g. `/v1/system/hold` or `/v1/zones/1`) and confirm within ~30 s the thermostat reflects it at the panel. Validated end-to-end on 2026-04-23 against alpha.10: PATCH cool=78 with `activateHold=true` → telemetry shows `currentActivity="manual"`, `hold.active=true`, panel displays HOLD; DELETE clears hold within ~60 s with matching panel behaviour.
8. **Stop the Perl add-on** (if installed and running) once the Python add-on has held steady for at least one full day of normal operation. Stopping it earlier is fine for freeing memory; keeping it running longer costs nothing and shortens rollback.

## Rollback procedure

> **Caveat for this deployment:** the legacy Perl add-on (`Infinitude Direct`) is *not currently installed* on the target HA host. Rollback therefore requires installing the Perl add-on from the store first before changing the thermostat proxy port back. Budget ~5 min extra before step 1 below if rollback fires. The add-on still lives in `infinitude/` in the repo until DESIGN.md Phase 7, so availability is not at risk — it's just an install step the baseline rollback plan doesn't account for.

Triggers (any one of these mandates rollback):

- Thermostat stops POSTing entirely for > 10 min with no observable error on the add-on side (may indicate protocol-level breakage the test suite missed).
- Add-on crashes repeatedly on startup.
- Thermostat rejects the proxy's response XML (visible in the device's local error reporting, or as a reboot loop).
- A user-initiated mutation via the API consistently fails to propagate to the thermostat after 3 attempts, including after forcing a `GET /config`.

Procedure:

1. **If the Perl add-on is not installed on this host:** install it from the HA add-on store (`Infinitude Direct`) and configure it; then continue. (See caveat above.)
2. **If the Perl add-on had been stopped:** start it (`Add-ons → Infinitude Direct → Start`). Port 3000 is still claimed by its config and no other service has taken it.
3. **Change the thermostat's proxy port from `3001` back to `3000`.** Same installer-settings field used for cutover, reversed. Save at the wall panel.
4. Confirm `/api/status` on the Perl add-on returns within ~90 s of thermostat activity.
5. Leave the Python add-on running on 3001 for post-mortem inspection; do not uninstall.
6. File a bug with the captured trigger state for triage.

Rollback window: unlimited. The Perl add-on remains in the repo until DESIGN.md Phase 7. No data-format changes lock us out.

## Post-cutover sequencing

In order, each shippable independently. Items marked **in progress** are already underway in parallel with the cutover plan — the original strict post-cutover ordering has loosened because the HA integration and card work are on the same alpha release train as the add-on (`2.0.0-alpha.x`) rather than waiting behind it.

1. **Capture live-traffic fixtures (24 h).** Regression-anchor work: capture-middleware tee of southbound POSTs + northbound reads for 24 h, curated into `addon/tests/fixtures/thermostat/live_YYYYMMDD/`. Replaces fixture serial `0000TEST0000` with real-shape fixtures across all mutation kinds and long-tail subpaths. Valuable but **not a prerequisite for the write-path fix** — that fix needs one real config, not a corpus.

   **Tooling shipped (alpha.11):** the capture middleware, `capture_traffic` SQLite table, and `/v1/debug/capture/*` control API are live. `addon/scripts/export_capture.py` pulls rows from a running addon's debug API and writes them out to a fixture-ready directory tree (organized by direction, one file per request body + one per response body, id zero-padded for lexical sort, `_index.tsv` summary). What remains is the ops sequence: `POST /v1/debug/capture/start` → let traffic accumulate → `python export_capture.py --base-url http://ha.local:3001 --out-dir captures/live_YYYYMMDD/` → `POST /v1/debug/capture/stop` → hand-curate the interesting bodies into `addon/tests/fixtures/thermostat/`.

   1a. **Write-path against live config — resolved in alpha.10 (2026-04-23).** Root cause: two wire-shape bugs in `mutations._set_or_create` and `apply_zone_hold_clear`. `text=""` rendered as `<tag></tag>` (lxml), but the thermostat's strict parser accepts only self-closing `<tag/>` for empty optional fields — any `<tag></tag>` occurrence caused a silent reject and a correction push of the previous config. Second bug: `apply_zone_hold_clear` wrote `<holdActivity>none</holdActivity>` for zones, but `"none"` is only valid at whole-house level; zones expect `<holdActivity/>` self-closing. Fix: `_set_or_create` now maps empty strings to `None` so lxml emits self-closing tags; `apply_zone_hold_clear` passes `""`. Byte-symmetry invariant `parse(x) → serialize → x` now proven against `boot_01_system_config.xml` as a regression anchor in `test_southbound.py`; explicit `<tag/>` shape assertions added to `test_zone_hold.py`. Live-fire confirmed round-trip on 2026-04-23 (see step 7 note above).
2. **HA integration cutover.** *(in progress)* `custom_components/infinitude_direct/` has already been rewritten to hit the `/v1/*` endpoints and ships alongside the add-on under the same alpha version. Post-cutover work here is narrowing to bug-fix + live-data validation rather than a net-new rewrite.
3. **Legacy HTML UI refresh.** *(in progress for humidity/vacation/service surfaces via the integration's Lovelace cards; `infinitude/infinitude-ui.html` itself is not being updated.)* The Python add-on does not serve the legacy Perl `infinitude-ui.html`; users get the new surfaces through the HACS integration's cards.
4. **Carrier passthrough implementation.** Not a cutover blocker for local-only use. Lands when needed by MyInfinity-app users.
5. **Perl add-on removal.** After 2 stable releases of the Python add-on. Final removal closes DESIGN.md Phase 7.

## Open items (decide before running the plan)

- **Carrier passthrough status at cutover time.** If Carrier passthrough ships *before* cutover, users of the MyInfinity app retain command-propagation parity. If it ships *after*, there is a gap where app-initiated changes rely solely on the thermostat's own Carrier polling (which still works — it's just no longer locally observed or rate-limited through the proxy). Default: accept the gap.
- **Who executes the cutover?** Assumes the repo owner. No operational runbook for a third party.
