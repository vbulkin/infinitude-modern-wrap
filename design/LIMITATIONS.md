# Limitations and propagation behavior (alpha.55+)

This document records what the addon CAN and CANNOT do with respect to the
three control surfaces (Home Assistant, the thermostat panel, the Carrier
MyInfinity app), the empirical evidence behind those limits, and the
user-visible consequences in normal operation.

It exists because earlier alphas shipped speculative architecture
(per-route auth caching, synthetic POST replay, grace-window pending-write
TTL) that didn't work in production and produced subtle revert/oscillation
behavior the user observed live. The cleanup in alpha.55 removed those
mechanisms; this document is what we keep instead.

## TL;DR

- **HA → thermostat**: works. Mutations land in the local tree; the
  thermostat pulls them on its next /config GET. Sub-minute end-to-end.
- **Thermostat panel → HA**: works. Panel changes show up in the
  thermostat's next status POST, which we mirror to Carrier; the
  thermostat then re-POSTs the new tree to /systems/{serial}, and we
  apply locally.
- **Carrier app → HA**: works **piggy-backed** on the thermostat's next
  /config GET (single-digit-minute latency, depending on the
  thermostat's poll cadence). The addon cannot pull from Carrier on its
  own.
- **HA → Carrier app**: does **not** propagate proactively. The Carrier
  app keeps showing pre-mutation state until the thermostat decides on
  its own to POST a fresh /systems/{serial} (boot, panel-edit, or its
  occasional unsolicited re-sync — observed empirically, hours apart).
- **Carrier app vs HA, concurrent edits**: out of scope. The system
  assumes you don't make conflicting changes from both surfaces inside
  the same minute or two. If you do, last-writer-wins, where "last" is
  whichever side the thermostat picks up later.

## What we proved by direct testing (2026-05-08)

Carrier's API uses OAuth 1.0 with HMAC-SHA1. We confirmed by capturing
real thermostat traffic and replaying / mutating it through the addon:

| Test | Result | Conclusion |
|---|---|---|
| Replay a captured Authorization header on the same URL | `<error><message>nonce has already been used</message></error>` | Nonce is single-use. |
| Replay it on a different URL | Same `nonce has already been used` error | Nonce is bound to the consumer/token, not the request. |
| Replay it on a different method | Same error | Per-route caching can't help. |
| Modify the body, leave headers original | `<error><message>signature doesn't match</message></error>` | Body is in the signed base string. |

This means the addon, which has access to:

- The thermostat's outbound traffic in real time
- The cached OAuth headers from any past request

cannot:

- Replay a captured OAuth header (single-use nonce)
- Forge a new one (consumer + token secrets are in firmware, never on
  the wire)
- Modify the body of an in-flight relay (body is signed)

The only way the proxy reaches Carrier is by **relaying a real
thermostat-originated request, byte-for-byte, while it's still in
flight** — which is exactly what the bridge does in `_outbound`.

## Propagation paths (state-machine view)

### HA → thermostat

1. User mutates via the API (`PUT /v1/system/hold`, etc.).
2. `state_store.mutate_config` rewrites the local config tree, marks
   `config_dirty=true`, and enqueues a `pending_writes` row for
   pull-observed-clear.
3. On the thermostat's next status POST we set `configHasChanges=true`
   in the directive response.
4. Thermostat pulls /config, we serve the mutated tree, mark the
   pending row applied, clear `config_dirty`.
5. Thermostat applies locally and re-POSTs the new tree to
   `POST /systems/{serial}`, which we mirror to Carrier. (This is also
   the **panel → Carrier** propagation path; see below.)

End-to-end latency: bounded by the thermostat's status-POST cadence
(`pingRate`), which Carrier sets dynamically (12 s clean / 20 s dirty
in our captures).

### Panel → HA → Carrier

1. User edits at the thermostat panel.
2. Thermostat POSTs the new full tree to `POST /systems/{serial}`.
3. We `apply_config` locally (HA sees the change).
4. We mirror the same body to Carrier (fire-and-forget) — Carrier
   accepts because the thermostat's OAuth is fresh and signed.

### Carrier app → HA (pull-through)

1. User changes something in MyInfinity.
2. Carrier flips `serverHasChanges=true` on the next status response.
3. We see it in the relay response; latch `pending_carrier_pull`.
4. On the thermostat's next /config GET, the southbound handler relays
   the GET to Carrier with the inbound thermostat headers (a real
   single-use OAuth signature for `GET /systems/{serial}/config`),
   parses the response, applies it to the local tree, and serves the
   merged tree back to the thermostat.
5. Any pending HA-side writes are replayed onto Carrier's tree before
   it's served, so a concurrent HA mutation isn't reverted by Carrier's
   stale view.

### HA → Carrier app — does **not** propagate proactively

This is the asymmetry that surprised us. There is no path:

- We can't push to Carrier (proven above).
- The thermostat **does** know HA mutated something — it just pulled
  our /config — but it has no way to distinguish "config came from
  Carrier" from "config came from HA". So when it next POSTs its
  current state to `/systems/{serial}`, it does so on **its own
  schedule** (boot, panel-edit, or occasional unsolicited re-sync),
  not synchronously after the HA mutation.

Concretely: a HA-set hold takes effect on the thermostat within ~20 s,
but the Carrier app may show the old state for **hours** until the
thermostat's next unsolicited boot/sync POST.

`serverHasChanges` does NOT help here. Carrier sets that flag based on
*its own* queued changes (MyInfinity edits). The Carrier cloud has no
way to know HA mutated the thermostat — it only sees a thermostat
status POST that reports the new state, and at that point the cloud
side just records it.

#### What this means for the user

- **Thermostat is authoritative for the system.** Both surfaces
  (HA, Carrier app) eventually agree once the thermostat re-syncs.
- **HA mutations are durable on the thermostat itself** — they aren't
  reverted by anything; the only mismatch is the Carrier app's *display*.
- **If you rely on the Carrier app for status**, expect it to lag HA
  edits by hours.
- **If you mutate from both HA and the Carrier app within the same
  ~minute**, behavior is undefined — last-writer-wins where "last" is
  whichever the thermostat sees second.

## Resilience contract (Carrier unreachable)

When Carrier is unreachable (DNS fails, internet down, 5xx, slow), the
addon must remain fully operational:

- Every outbound call is bounded by a 3 s timeout.
- A circuit breaker opens after 3 consecutive failures and stays open
  with exponentially-growing cooldown (30 s → 60 s → … → 5 min cap).
  While open, calls short-circuit without touching httpx.
- All thermostat-facing endpoints serve local content and never block
  on Carrier latency.
- When Carrier comes back, propagation resumes naturally on the next
  thermostat status POST. There is no "catch-up" mechanism — HA
  mutations made during the outage propagate to the thermostat as
  normal (they were never lost; they're in the local tree). They reach
  the Carrier app on the same indirect schedule as in steady state.

## Out of scope

- **Optimistic concurrency / merge resolution** between HA and Carrier
  edits. The system is single-writer-at-a-time per setting.
- **Carrier-app-only features** that aren't reflected in the config
  tree (geofencing, automation rules running on Carrier's side, etc.).
  These continue to work on the Carrier side but aren't visible to HA.
- **Pushing HA changes to Carrier through any other channel.** We
  considered (and removed in alpha.55) synthetic boot POSTs, per-route
  cached headers, body modification, etc. None work. Reaching the
  Carrier app from HA requires the thermostat as a courier, on its own
  schedule.

## Empirical evidence

The OAuth probes are reproducible against the addon's debug capture
endpoints; see git history around 2026-05-08 for the test scripts and
captured Carrier responses. The propagation observations are based on
multiple weeks of live operation against a single Greenspeed install
(model `systxbbec`, firmware 14.02).
