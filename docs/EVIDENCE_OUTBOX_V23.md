# APCS v2.3 Evidence Capture / Outbox

Status: **Gate B1**

The v2.3 learning system separates:

```text
local learner mutation
from
remote durable Notion writeback
```

A successful local attempt must not depend on network availability.

## Runtime flow

```text
VS Code attempt
  -> capture immutable attempt facts
  -> capture explicit Skill x Track evidence claims
  -> append local outbox envelope
  -> update local adaptive-memory state when evidence is complete
  -> retry Notion REC / Evidence writeback independently
  -> store local receipt
```

The outbox default location is local runtime state under:

```text
.apcs/runtime/outbox/
```

and is excluded from Git.

## Envelope model

One envelope corresponds to one finished attempt.

It contains:

- stable `attempt_id`;
- stable `writeback_id`;
- Problem ID / optional PB UID;
- timezone-aware start / finish timestamps;
- language;
- judge result;
- Assistance A0-A5 when known;
- Independent when known;
- attempt count when known;
- active minutes when known;
- novelty when known;
- Activity when known;
- zero or more explicit Evidence claims.

## Evidence claim

One Evidence claim means:

```text
one Skill x one Track observation
```

Examples:

```text
S22_Prefix_Sum x Implementation = PASS
S30_Complexity x Reading = PASS
```

The outbox deliberately does **not** infer Evidence from all Problem Tags.

An AC on a Prefix Sum problem does not automatically prove every supporting
Skill.

## Unknown facts stay unknown

This is intentional:

```text
assistance = unknown
independent = unknown
novelty = unknown
```

is valid durable attempt data.

But incomplete evidence context cannot update the adaptive memory engine.

The runtime must never silently convert unknown values into:

```text
A0
independent=true
fresh transfer
```

because that would inflate the learner model.

## Idempotency

Each envelope has a stable `writeback_id`.

Each Evidence claim has a stable `event_id`.

Remote Notion writeback must use those IDs as idempotency keys.

Therefore this failure mode is safe:

```text
Notion write succeeds
process crashes before local receipt
restart
retry same envelope
Notion detects same writeback_id / event_id
no duplicate durable record
```

## Local receipt

A successful remote writeback does not delete the local attempt envelope.

Instead, a receipt is stored separately.

Benefits:

- audit / reconciliation remains possible;
- pending queue is simply "envelopes without receipts";
- a conflicting second receipt is rejected.

## Crash boundary

Local envelope persistence uses same-directory atomic replacement.

The authoritative user-facing rule is:

```text
attempt captured locally
=> learner action is complete

Notion writeback unavailable
=> pending sync
=> do not repeat the problem just to recreate the record
```

## Relationship to adaptive memory

Complete explicit evidence can be converted into the v2.3 adaptive model:

```text
OutboxEnvelope
  -> Memory Evidence
  -> Skill x Track Stability / Retrievability
```

Incomplete attempts still remain valid REC candidates, but they are not used to
inflate memory state.

## Current Gate B1 scope

Implemented:

- durable envelope schema;
- explicit attempt facts;
- Skill x Track evidence claims;
- unknown-value preservation;
- idempotent enqueue;
- conflicting writeback rejection;
- independent remote receipts;
- pending queue;
- adaptive-memory conversion;
- regression tests.

Not implemented yet:

- Notion writer adapter;
- VS Code interactive capture UI;
- automatic Problem -> Placement context;
- learner-facing reconciliation screen.

Those belong to the next gates.

## Acceptance invariants

- one learner attempt is captured once;
- writeback retry does not create a second local attempt;
- one attempt contains at most one claim per Skill x Track;
- Problem tags never automatically become evidence;
- unknown evidence-quality facts stay unknown;
- incomplete evidence cannot alter adaptive memory;
- remote sync failure does not invalidate the local attempt;
- pending writeback is operational state, not learning debt.


## v2.3 remote writeback contract hardening

The outbox contract is now projected through `tools/remote_writeback.py`.

Additional invariants:

- Published PB UID is required before an envelope is remotely eligible;
- local `writeback_id` becomes REC idempotency identity;
- local `event_id` becomes EV-v1 idempotency identity;
- exact `finished_at` is preserved for delayed/offline synchronization;
- MLE, Transfer, Mixed, and Same Problem Repeat are preserved losslessly;
- relations are sent as PB UID / Skill UID identities and resolved only by the
  trusted server;
- the client never supplies `Valid for Gate`;
- a local receipt must represent one complete REC plus the exact expected
  Event ID set before the envelope can leave the pending queue.

The production network transport remains disabled until the active Cloudflare
Worker source is patched and verified.  See `docs/REMOTE_WRITEBACK_V23.md`.
