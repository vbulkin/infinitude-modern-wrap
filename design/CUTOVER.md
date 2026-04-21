# Infinitude Proxy — Cutover Plan (Perl → Python)

Operational plan for replacing the legacy `infinitude/` (Perl/Mojolicious) add-on with the new `addon/` (Python/FastAPI) add-on in a deployed Home Assistant instance.

Companion to [`DESIGN.md`](./DESIGN.md) §13 (migration phases). This doc answers the question: *given the Python proxy is code-complete, what's the safe procedure to flip production traffic?*

## Scope

- **In scope:** switching a single HA host's thermostat from the Perl add-on to the Python add-on, including pre-cutover validation, rollback procedure, and post-cutover follow-ups.
- **Out of scope:** HA integration rewrite and legacy HTML UI refresh. Those start *after* cutover lands; they're tracked separately and are explicitly sequenced post-cutover so we don't chase moving targets (see DESIGN.md §13 Phase 5/6).

## Key facts driving the plan

- **Single thermostat, single HA host.** Not a fleet migration — no canary / percentage rollout.
- **Thermostat addressing is redirect-based.** The thermostat speaks to whatever host/IP the LAN's DNS or hosts-override sends its Carrier hostnames to. Currently that's the HA IP on port 3000. Switching proxies means swapping what's bound to that port, not re-flashing the thermostat.
- **Both add-ons claim port 3000.** Can't run both at once on the same port; parallel validation runs require the new add-on on a different port (e.g. 3001) and the tester to send traffic explicitly to that port.
- **Persistence is local.** The Python add-on's SQLite lives in `/data/` (HA add-on convention). A full rehydrate from scratch takes one `<config>` POST (≤ a few seconds after the first thermostat tick). No data migration from the Perl add-on is required or possible — shapes differ.
- **Carrier cloud passthrough is not yet implemented** in the Python proxy. Cutover with passthrough-dependent features (e.g. MyInfinity app → thermostat changes) will delay those commands by up to the next manual hard-refresh. See §"Open items" below.

## Prerequisites (must be green before cutover)

- [ ] **Full Python test suite green** (`pytest` in `addon/`). Current: 224 passing.
- [ ] **Schemathesis contract smoke** against a live Python add-on instance (openapi.yaml round-trip).
- [ ] **Boot-sequence replay** — the Perl add-on's captured thermostat boot POSTs (`boot_01..06`) drive the Python southbound handler without error; state projects to the expected shape on `GET /v1/state`.
- [ ] **Steady-state replay** — `telemetry_steady.xml` POSTed 10× in a row; state-store stays internally consistent, SSE emits one `state.update` per POST.
- [ ] **Write round-trip** — PATCH `/v1/zones/1` → `config_dirty=true` → directive signals → manual GET `/systems/{serial}/config` serves mutated XML → pending row clears. Covered by tests; re-verify against a live instance.
- [ ] **Restart replay** — kill/restart the add-on between a pending write and the thermostat's `GET /config`: on restart, the pending row survives, `apply_config` replays it onto the next thermostat POST, and the mutation is not lost.
- [ ] **Docker image builds clean** for all four HA architectures listed in `config.yaml` (`aarch64 / amd64 / armhf / armv7`).
- [ ] **Capture fixtures frozen** — `addon/tests/fixtures/thermostat/` contains one full boot sequence + one user-action telemetry delta + one notifications batch from the actual thermostat that's about to be cut over. Pull fresh captures if the on-device firmware has moved since the last snapshot.
- [ ] **`/v1/healthz` returns `status: healthy`** once live telemetry is flowing (stale threshold 300 s).

## Pre-cutover: parallel-run validation window

Goal: prove the Python proxy handles the specific thermostat's traffic before retiring the Perl one.

1. **Install both add-ons, different ports.** Reconfigure the Python add-on's `config.yaml` to bind `3001/tcp: 3001` and `ingress_port: 3001`. Leave the Perl add-on on 3000 as the live serving path.
2. **Mirror-capture from the thermostat.** Use `mitmproxy` / `tcpdump` on the HA host (or at the LAN boundary) to record the next ~24 h of thermostat traffic landing on port 3000. This is the replay corpus for step 3. Store under `captures/cutover_window_<date>/`.
3. **Replay into the Python add-on on 3001.** Write a one-shot script that POSTs the captured bodies at their recorded cadence against `http://127.0.0.1:3001/systems/...`. Compare:
   - Response status codes (both must be 200).
   - `<directive>` element contents for status POSTs (both must make the same `configHasChanges` / `pingRate` decisions given the same dirty state).
   - `GET /config` byte-for-byte when no pending writes are queued.
   - `/v1/state` on the Python add-on is sensible after each replay tick.
4. **Drive the northbound API live.** Hit every mutating endpoint on the Python add-on during the validation window. A shell script walking each PATCH/PUT/DELETE with realistic payloads is sufficient.
5. **Observe SSE for 1 h.** Subscribe with `curl -N http://127.0.0.1:3001/v1/events`; confirm `state.snapshot` on connect, `state.update` on each replay tick, `hold.changed` on each hold PATCH, and SSE comment pings every 15 s.

Any discrepancy in steps 3–5 is a cutover blocker. File, fix, re-run validation.

## Cutover procedure

Once the validation window closes green:

1. **Announce downtime** to housemates: "thermostat proxy offline, ~2 min." In practice the thermostat continues to run locally; only the HA UI loses fresh data during the gap.
2. **Back up the Perl add-on's state.** From the HA host: copy the legacy add-on's data directory to a safe location. Belt-and-suspenders — the Python add-on won't read it, but if rollback is needed this data is what the Perl add-on boots from.
3. **Stop the Perl add-on.** HA → Add-ons → Infinitude Direct → Stop.
4. **Reconfigure the Python add-on back to port 3000.** Edit `addon/config.yaml` (or the HA options UI if schema allows): `ingress_port: 3000`, `3000/tcp: 3000`.
5. **Start the Python add-on.** HA → Add-ons → Infinitude Modern Proxy → Start.
6. **Watch the first thermostat tick.** Tail add-on logs. Within ~90 s (one telemetry cadence) the thermostat will POST `/status`; logs should show parser success and state-store update. Within the next few minutes the boot-shaped POSTs (`/config`, `/idu_config`, `/odu_config`, `/notifications`) will flow as part of steady-state operation or a forced reboot.
7. **Force a thermostat reboot** (at the wall panel or via a power-cycle) if step 6 doesn't produce a full boot sequence within 10 minutes — the state store rehydrates cleanly on boot and this reduces the post-cutover warm-up window.
8. **Validate.** Hit `/v1/healthz` — `thermostat.status` should be `healthy`. Confirm `/v1/state` shows accurate live values. Try one PATCH (e.g. `/v1/system/hold`) from `/docs`; confirm within ~30 s the thermostat reflects it at the panel.

## Rollback procedure

Triggers (any one of these mandates rollback):

- Thermostat stops POSTing entirely for > 10 min with no observable error on the add-on side (may indicate protocol-level breakage the test suite missed).
- Add-on crashes repeatedly on startup.
- Thermostat rejects the proxy's response XML (visible in the device's local error reporting, or as a reboot loop).
- A user-initiated mutation via the API consistently fails to propagate to the thermostat after 3 attempts, including after forcing a `GET /config`.

Procedure:

1. Stop the Python add-on.
2. Change its port binding back to 3001 (or whatever non-conflicting port) in `config.yaml`.
3. Start the Perl add-on.
4. Confirm `/api/status` on the Perl add-on returns within ~90 s of thermostat activity.
5. File a bug with the captured trigger state for triage.

Rollback window: unlimited. The Perl add-on remains in the repo until DESIGN.md Phase 7. No data-format changes lock us out.

## Post-cutover sequencing

In order, each shippable independently:

1. **Capture live-traffic fixtures.** Immediately after cutover, with the Python proxy live, record another 24 h of traffic and extend the fixture suite. These are high-value regression anchors for all future slices.
2. **HA integration cutover.** Single PR updating the HA coordinator (`custom_components/infinitude/`) to hit the `/v1/*` endpoints. Major-version bump on the integration. Legacy `/api/*?mode=…` query-string calls are deleted in the same commit.
3. **Legacy HTML UI refresh.** Expose the new surfaces the legacy UI doesn't have today: humidity targets (`/v1/system/humidity`), vacation scheduling (`/v1/system/vacation`), service-reminder levels (`/v1/system/service`). These may or may not go into `infinitude/infinitude-ui.html` depending on whether that UI is retained or replaced wholesale.
4. **Carrier passthrough implementation.** Not a cutover blocker for local-only use. Lands when needed by MyInfinity-app users.
5. **Perl add-on removal.** After 2 stable releases of the Python add-on. Final removal closes DESIGN.md Phase 7.

## Open items (decide before running the plan)

- **Validation window length.** 24 h is the default above. Longer (48–72 h) gives more confidence at low cost; shorter is risky if the thermostat has infrequent event types we miss.
- **Parallel run vs. hard cut.** This plan uses a parallel-run validation window with the Python add-on on a non-serving port. An alternative is a hard cut with no prior live validation — cheaper operationally, higher risk. Default: parallel run.
- **Carrier passthrough status at cutover time.** If Phase 7-ish Carrier passthrough ships *before* cutover, users of the MyInfinity app retain command-propagation parity. If it ships *after*, there is a gap where app-initiated changes rely solely on the thermostat's own Carrier polling (which still works — it's just no longer locally observed or rate-limited through the proxy). Default: accept the gap.
- **Who executes the cutover?** Assumes the repo owner. No operational runbook for a third party.
