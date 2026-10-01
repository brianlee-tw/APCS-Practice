# APCS v2.3 Remote Writeback Contract

Status: **contract implemented; production transport not yet enabled**

This contract defines the boundary between the durable VS Code outbox and the existing Cloudflare / Notion Direct Write architecture. It does not claim that production remote synchronization is live.

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

VS Code Direct requires the live schema to preserve `Writeback ID`, `PB UID`, `Problem ID`, Judge result including MLE, `紀錄來源 = VS Code Direct`, `紀錄性質 = 正式紀錄`, and `Attempt Finished At`, plus optional language / Assistance / Independent / attempts / time. The original attempt timestamp is preserved even if remote sync happens later.

`學習階段` is presentation metadata derived from explicit Activity / Timed / Independent attempt facts; it is not a capability axis.

## EV-v1 projection

The live Evidence Ledger supports `Event ID`, Track, Activity, Outcome, Judge Result including MLE, Assistance, Independent, Timed, Time min, Date, relations, Evidence Note, and Novelty values New / Seen / Delayed Retest / Transfer / Mixed / Same Problem Repeat.

## Gate boundary

The client **does not write `Valid for Gate`**. Durable persistence and mastery evaluation stay separate:

    durable EV-v1 event
    -> versioned MEAS evaluator
    -> Valid for Gate / RM / IM proposal

Successful sync means Evidence is durable. It does not mean mastery or RR/IR readiness passed. `LEARNER_READINESS` remains evidence-derived.

## Existing /api/record compatibility

The existing production browser request stays REC-only. The intended Worker extension is a second payload variant on the same versionless `POST /api/record`, selected by `schema_version = v2.3-remote-writeback-1`. Existing HTML Direct payloads remain unchanged.

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

Implemented:
- `tools/remote_writeback.py`: deterministic bundle and logical REC/EV projection.
- `tools/writeback_sync.py status`: read-only pending / eligible / blocked inspection.
- `tools/writeback_sync.py bundle <writeback_id>`: canonical JSON export.
- `tools/writeback_sync.py bundle <writeback_id> --projection`: logical Notion projection.

Not yet implemented:
- network POST;
- Worker bundle variant;
- write-key integration;
- production receipt ingestion;
- live REC+EV E2E.

Those final items require the active Cloudflare Worker source / deployment environment.