# APCS v2.3 Adaptive Today Runtime

Status: **Gate B3**

The learner-facing entry point is now **Today learning**, not a permanent problem-level review queue.

## Goal

The system should answer what to do today, how much old material to maintain, how much capacity stays available for new learning, which Skill is at retention risk, and which problem can test it without showing the historical answer.

It must not turn solved-problem count or overdue-problem count into a backlog that blocks new learning.

## Runtime flow

Durable local Evidence envelopes → reconciliation → Skill × Track memory cache → Stability / Retrievability → due Skill candidates → capacity governor → Today learning plan.

The memory file under .apcs/runtime/skill_memory.json is **derived cache**, not learner truth. It can be rebuilt from durable Evidence envelopes.

## Persistence invariants

The memory cache is atomically written, schema/version aware, idempotent by Evidence event ID, rebuilt after policy-version changes, and rebuilt if late or out-of-order Evidence arrives. Incomplete Evidence is skipped rather than guessed.

## Today capacity

Default session capacity is 60 minutes. Default review target is 18 minutes. Under the default policy this leaves at least 42 minutes for new learning.

APCS_SESSION_MINUTES can adjust session capacity within 15–240 minutes. APCS_TARGET defaults to 3+3 and may be set to 5+5. These environment variables are transitional configuration.

## No review debt

If 20 Skills are technically due but only 2 fit the review budget, 2 are selected and 18 are deferred. Deferred Skills are not missing homework; they are ranked again next session.

## Candidate priority

Review selection remains transparent: recent failure, curriculum importance, lower Retrievability, greater overdueness, then shorter task that fits remaining capacity.

Curriculum importance is read from the published curriculum snapshot. Missing curriculum data is reported rather than invented.

## Review problem selection

For Implementation review, the runtime chooses a Published Placement whose Primary Skill matches the due Skill. It prefers an unattempted problem before a previously used one, and then prefers Transfer Challenge, Core Independent, Guided Drill, Worked Example, then Mock.

This preference is task selection only; it is not mastery logic.

## Blank retrieval scratch

The system does not open the learner's historical solution for adaptive Implementation review. It creates .apcs/runtime/review/<date>/<problem_id>__<placement_uid>.cpp containing Skill, Problem title, Role, Judge URL when available, and a blank C++ skeleton.

The Placement UID is preserved when the learner later records Review evidence, preventing the review from silently attaching to a different curriculum context.

## Reading Track

Reading review deliberately does not open a historical solution or execute code automatically. Formal Reading evidence must preserve the MEAS rule: reason or trace first, no executor before the formal response.

## Relationship to v2.2 data

The old progress.csv / reviews.csv problem-level review state remains temporarily for compatibility and historical continuity, but it is no longer the learner-facing Today scheduler.

New v2.3 scheduling is explicit Evidence → Skill × Track memory → capacity-aware Today.

The old fixed-interval path is retired from tools/vscode_task.py so a hidden compatibility command cannot bypass the v2.3 Evidence model.

## Failure behavior

If memory-cache update fails after an Attempt was safely captured, the Attempt remains complete, the Evidence envelope remains durable, and the memory cache is rebuilt later. The learner must not repeat the problem merely to reconstruct system state.

## B3 acceptance

- durable Evidence can rebuild memory state;
- repeated reconciliation is idempotent;
- policy change triggers rebuild;
- out-of-order Evidence triggers rebuild;
- due selection is Skill × Track based;
- daily review remains capacity bounded;
- deferred items are not debt;
- Today no longer opens historical solutions;
- Published Placement selects the review context;
- missing curriculum data is reported rather than guessed;
- old fixed-interval VS Code Task entry points cannot silently bypass v2.3.

## Next learner-value gate

B4 should focus on the new-learning side of Today: current curriculum route → next ready Skill → lesson/prerequisite context → guided or independent Practice → Evidence.

Only after that should Today be considered a complete learning planner rather than a high-quality adaptive maintenance planner.
