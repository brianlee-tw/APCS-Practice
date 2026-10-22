# APCS C++ Learning System | Stage L — Local Judge → Attempt → Evidence Trust Boundary

**Review date:** 2026-10-22 (Asia/Taipei)  
**PR:** [#89](https://github.com/brianlee-tw/APCS-Practice/pull/89), Draft and unmerged  
**Decision:** ENGINEERING_TESTS_PASS / GENUINE_LEARNER_ACCEPTANCE_PENDING  
**Authority:** Published Curriculum / Notion are unchanged; these tests are engineering-only and do **not** generate learner Evidence or certify Readiness.

## Verified existing product behavior

The local Test Center runs `tools/local_test_runner.py`, where per-test statuses include `PASS`, `WRONG_OUTPUT`, `TIMEOUT`, `RUNTIME_ERROR`, `OUTPUT_LIMIT` and `UNVERIFIED`. It may execute ordinary exact-output tests and the source-pinned CF 977C semantic checker. **Local PASS is not OJ AC.**

In `tools/vscode_task.py`, Test Center shows its local summary, and the link/open-to-OJ action explicitly instructs the learner to return to the Control Center and obtain or record the official OJ verdict; opening a browser does not itself submit or produce Evidence. The local Test Center runner contains **no path that automatically calls the durable Evidence Outbox**.

For Published practice, `tools/apcs_control.py` asks for an explicit OJ verdict unless current selected Exam Runtime telemetry has a relevant `SUBMIT`. It separately records Assistance / Independent / Novelty / Timed, does not infer AC from local runs, and distinguishes `Reading` assessments from `Implementation` OJ verdicts. `attempt_envelope_for_record` limits an Implementation claim to the Published Primary Skill. For method_confirmation_required placements, unconfirmed target method yields Attempt-only with no Skill Evidence. `memory_evidence` converts only complete explicit learner facts.

Note: The workflow uses user-entered OJ verdict or Exam Runtime submit telemetry; in this Pilot **it does not perform independently authenticated remote OJ result retrieval**. An OJ AC reported in the UI remains an entered/recorded verdict, not a directly verified API response.

## Findings and minimal repairs

### 1. Exam Runtime stale-verdict bug

Before: `inferred_published_result` could find an older AC for the same problem even after the learner switched to a different problem and later returned, because it checked only selected_problem_id and searched all earlier SUBMIT events.

After: new pure `exam_verdict_for_current_selection` requires an explicit current SELECT/SWITCH epoch and will only reuse a SUBMIT **after that most recent selection event**. It blocks old AC after switch-away/back, refuses missing/malformed selection history, and refuses inheriting older AC when a newer SUBMIT has N/A. The existing C8 synthetic test fixture now includes the legitimate SELECT event that actual Exam Runtime records.

Limits: Exam `SUBMIT` is recorded user/OJ telemetry; this does not authenticate the remote judge, and cannot independently detect an unsent resubmission after the last logged SUBMIT.

### 2. A2+ Independent data-layer contradiction

Before: assistance-dependent independence is enforced in the menu, but a raw or replayed outbox envelope could set `assistance >= 2` and `independent=true`, causing adaptive memory to ingest contradictory mastery evidence.

After: `AttemptFacts.__post_init__` refuses any explicit A2–A5 / independent=true combination, including when deserializing persisted or externally supplied envelopes. Unknown fields remain unknown; we do not assume A0 or independent=true.

### 3. OJ verdict ↔ Implementation claim contradiction

Before: `memory_evidence` received explicit claims and could be asked to convert an Implementation PASS whose attempt judge_result was WA or N/A (or an Implementation FAIL paired with AC). The first repair made the adaptive-memory conversion fail closed; a subsequent review identified that a contradictory claim should be rejected **before** writing the durable outbox, not only at memory reconciliation time.

After: `OutboxEnvelope.__post_init__` rejects inconsistent Implementation claim/verdict combinations before `OUTBOX.enqueue` or remote writeback. `memory_evidence` additionally enforces the same check as defense-in-depth. Legitimate mixed-track attempts (Implementation + Reading) remain permitted and retain separate Skill x Track semantics. Reading-only responses do not need an OJ AC.

### 4. Regression fixture repair

The older `test_evidence_outbox_v23` conflicting-writeback test had a `WA + Implementation PASS` synthetic envelope; that was invalid under the strengthened contract. Its purpose (reject a conflicting payload with the same writeback_id) is now tested with a different **valid** note field rather than a contradictory verdict.

## Engineering test evidence

New `tests/test_pilot_evidence_trust_boundary.py` exercises:

- Correct current-selection Exam SUBMIT AC / WA reuse, stale AC after switch-away and back, latest N/A blocking old AC, no inference without a selection.
- Local `PASS` and `WRONG_OUTPUT` from a real temporary-process run, with assertions that Outbox.enqueue and adaptive Memory.reconcile were **not called**.
- Attempt judge_result `PASS` rejected (not a valid OJ verdict); contradictions such as `WA + Implementation PASS`, `N/A + Implementation PASS`, or `AC + Implementation FAIL` rejected before durable storage.
- A2–A5 + independent=true rejected both for raw input and for serialized-envelope replay. Assisted A2+ evidence can remain independent=false.
- Mixed Reading + Implementation claims still correctly supported.
- No real user Attempt/Evidence record, OJ submission, Notion page, or Published Curriculum entry modified.

**APCS Validate #354 PASS** (metadata + changed-solutions jobs) at code/test commit `1093cdb3b1b43a78d198bf8f5562b484f18fd319`. The final docs-only commit should receive its own CI status independently.

## Remaining limits and next gate

- Existing learner records were not migrated or rewritten. A legacy inconsistent record, if any, would now be rejected instead of silently included in memory; remediation requires inspecting the real record and preserving provenance.
- New local tests do not prove a learner correctly solved any APCS problem, nor that external OJ AC was authenticated. They do not close C8.
- This branch still needs genuine user Windows / WSL / VS Code acceptance and explicit authorization before any merge. The release preflight remains `BLOCKED_MANUAL` and `LEARNER_READINESS=NOT_ASSESSED`.
- Long-term follow-up: decide whether explicit verdict provenance (user-entered vs independent remote source) should become an optional versioned field after C8; do not improvise an external judge connector or break v2.3 schema in this pilot.
