# APCS v2.3 Remote Writeback Contract

Status: **Cloudflare/Notion server production active; client transport implemented on this branch**

This contract defines the boundary between the durable VS Code outbox and the existing Cloudflare / Notion Direct Write architecture. Cloudflare Worker #51 is production-active for the v2.3 REC+EV bundle variant; this branch adds the local client transport that turns a validated remote receipt into a durable local acknowledgement.

## Flow

    VS Code Finish / Review
    -> immutable OutboxEnvelope
    -> canonical v2.3 remote bundle
    -> trusted Cloudflare Worker
    -> REC-v3.1 + EV-v1
    -> complete remote receipt
    -> local mark_sent()

Notion API credentials remain server-side only.

## Identity and idempotency

- One attempt transaction is identified by `writeback_id`.
- Each EV-v1 event is identified by `event_id`.
- REC retry must reuse the existing row with the same `writeback_id`.
- EV retry must reuse the existing row with the same `event_id`.
- Conflicting identity reuse is a hard failure.
- Local `mark_sent()` occurs only after the server proves the REC and every expected EV event are durable.

This makes REC-success / partial-EV / connection-loss / retry safe without duplicate durable records.

## Canonical bundle

Schema: `v2.3-remote-writeback-1`.

The bundle preserves exact attempt facts: attempt/writeback identity, PB UID, Problem ID, timestamps, language, Judge result, Assistance, Independent, attempt count, active minutes, Timed, Novelty, Activity, source, and note. Each Evidence item additionally preserves event ID, Skill UID, Track, Outcome, and Evidence Note.

Unknown facts remain unknown. They are not defaulted.

## Relation resolution

The client sends canonical PB UID / Skill UID / writeback ID, not Notion page URLs. The trusted Worker resolves those identities against live Problem Bank, Skill Map, and REC-v3.1 SSOT. Repository Tags, titles, relation order, and stale page IDs are not relation authority.

## REC-v3.1 projection

VS Code Direct requires the live schema to preserve `Writeback ID`, `PB UID`, `Problem ID`, Judge result including MLE, `紀錄來源 = VS Code Direct`, `紀錄性質 = 正式紀錄`, `Attempt Started At`, `Attempt Finished At`, and `Independent Known`, plus optional language / Assistance / Independent / attempts / time. The original attempt timestamps are preserved even if remote sync happens later; `Independent Known` distinguishes an explicit false from an unknown checkbox value.

`學習階段` is presentation metadata derived from explicit Activity / Timed / Independent attempt facts; it is not a capability axis.

## EV-v1 projection

The live Evidence Ledger supports `Event ID`, Track, Activity, Outcome, Judge Result including MLE, Assistance, Independent, Independent Known, Timed, Timed Known, Time min, Date, relations, Evidence Note, and Novelty values New / Seen / Delayed Retest / Transfer / Mixed / Same Problem Repeat. The Known flags preserve unknown-vs-false semantics for Notion checkboxes.

## Gate boundary

The client **does not write `Valid for Gate`**. Durable persistence and mastery evaluation stay separate:

    durable EV-v1 event
    -> versioned MEAS evaluator
    -> Valid for Gate / RM / IM proposal

Successful sync means Evidence is durable. It does not mean mastery or RR/IR readiness passed. `LEARNER_READINESS` remains evidence-derived.

## Existing /api/record compatibility

The existing production browser request stays REC-only. Production Worker #51 accepts a second payload variant on the same versionless `POST /api/record`, selected by `schema_version = v2.3-remote-writeback-1`. Existing HTML Direct payloads remain unchanged.

The repository does not invent an auth header. The active Worker must reuse its existing trusted write-key mechanism; Notion credentials never move to the client.

## Required server transaction

1. Authenticate using the existing Worker mechanism.
2. Validate bundle schema.
3. Resolve PB UID through Problem Bank SSOT.
4. Query REC by Writeback ID; create if absent, otherwise verify and reuse.
5. For every Evidence item, resolve Skill UID, query by Event ID, create if absent or verify/reuse, and link Problem / Skill / Solve Record.
6. Verify the complete expected Event ID set exists.
7. Return one complete receipt. Partial results are not complete.

## Receipt contract

Target response fields: schema version `v2.3-remote-receipt-1`, matching writeback ID, `complete=true`, REC page ID + duplicate flag, and one Evidence receipt per expected event ID with page ID + duplicate flag.

Only a complete, identity-matching receipt may be persisted locally.

## Fail closed

Remote sync remains pending for missing/unresolvable PB or Skill identity, identity conflicts, partial response, auth failure, network failure, or invalid response shape. The learner does not repeat the problem to repair transport state.

## Current implementation boundary
Implemented and verified:

- `tools/remote_writeback.py`: deterministic canonical bundle, REC/EV
  projection, and complete receipt validator.
- production Cloudflare Worker #51:
  `6c1e4f06-d7c5-4a33-91eb-9b788386a23d`.
- production deployment:
  `e7641e63-7d35-4468-8369-5072b94b15f2` at 100%.
- authenticated live REC+EV creation and exact retry idempotency: PASS.
- test-row cleanup plus independent Notion cleanup query: PASS.
- `tools/remote_transport.py`: fixed-origin HTTPS adapter.
- `tools/writeback_sync.py configure-key`: local credential setup without
  storing authorization material in Git or outbox envelopes.
- `tools/writeback_sync.py sync <writeback_id>`: one-envelope sync.
- `tools/writeback_sync.py sync-pending [--limit N]`: durable-order retry.
- HTTP/network/receipt failure leaves the envelope pending.
- `validate_remote_receipt()` always runs before `mark_sent()`.

Production client configuration:

    export APCS_WRITEBACK_URL='https://apcs-rec-writeback.main-1h9k2.workers.dev/api/record'
    python3 tools/writeback_sync.py configure-key
    python3 tools/writeback_sync.py status
    python3 tools/writeback_sync.py sync-pending

The write key may alternatively be supplied through the `APCS_WRITE_KEY`
environment variable. The endpoint must be explicitly configured and must
match the approved production URL; a missing or different endpoint fails
closed before any network request.

The learner must never repeat a problem solely to repair synchronization.
`LEARNER_READINESS = NOT ASSESSED` remains unchanged.
