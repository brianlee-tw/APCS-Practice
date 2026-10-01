# APCS v2.3 B4 New Learning Route

Status: **Gate B4**

B4 completes the new-learning side of Today without changing the canonical
mastery/readiness system.

## Runtime flow

```text
Published Curriculum
  +
durable local Evidence envelopes
  ↓
conservative MEAS-v1 Skill × Track lower bound
  ↓
target Required Skills + transitive prerequisites
  ↓
B4 start-threshold check
  ↓
current Learning Skill or next Ready Skill
  ↓
Lesson / Placement context
  ↓
Guided or Core practice
  ↓
Finish → durable Evidence outbox
```

Adaptive-memory Retrievability is not used to decide whether a prerequisite is
mastered.  It remains a retention/review signal only.

## Start threshold

B4 policy version: `b4-start-v1`.

A prerequisite Skill is allowed to unlock a dependent Skill when at least one
of its applicable Tracks has durable Evidence supporting Level 2 or higher.

For the current curriculum every Skill supports both Reading and
Implementation, so examples include:

```text
RM≥2 / IM0  → start-ready
RM0 / IM≥2  → start-ready
RM1 / IM1   → not start-ready
```

This is deliberately a **start threshold**, not a mastery or readiness verdict.

- It does not claim RM3 / IM3.
- It does not claim RR / IR.
- It does not make Lesson completion into Evidence.
- It does not use manual Notion Skill Status.
- It does not use adaptive-memory Retrievability.
- It does not let one strong Skill compensate for a missing prerequisite Skill.

Full RM/IM and RR/IR readiness remain governed by MEAS-v1.

## Conservative Evidence lower bound

The runtime only promotes the lower bound from explicit PASS Evidence whose
Attempt facts are sufficient.

Key rules implemented for route selection:

- Worked Example: learning material; no independent Gate promotion.
- Guided PASS with Assistance at most A3 can support Level 1.
- Standard Guided/Core PASS with Assistance at most A2 can support Level 2.
- Implementation Level 2 additionally requires Judge result AC.
- Core Independent PASS with A0-A1, Independent=true, and non-seen novelty can
  support Level 3.
- New Transfer PASS with A0-A1 and Independent=true can support Level 4.
- Same-problem immediate repeat cannot unlock Level 2.
- Level 5 is not inferred by B4 because MEAS-v1 requires cross-date delayed and
  timed mixed/Mock portfolio composition.

These values are lower bounds used for routing.  They are not a parallel
mastery ledger.

## Target route

For the selected `APCS_TARGET`:

1. start from Skills whose relevance is exactly Required;
2. add their transitive prerequisite Skills;
3. do not add unrelated Supporting, Bridge, or Extension Skills;
4. sort deterministically by Path Order;
5. prefer an already-started Learning Skill before opening another Ready Skill.

Therefore Supporting or Extension content does not become a hidden universal
requirement.  It only enters the route when the published prerequisite graph
actually requires it.

## Placement action

For a fresh Skill, B4 prefers:

```text
Guided Drill
→ Core Independent
→ Worked Example fallback
→ Transfer fallback
```

For a Skill that already has Level-1 Evidence, Core Independent is preferred
before another Guided Drill.

The selected Placement is explicit and its `placement_uid` is embedded in the
runtime scratch filename.

## Published runtime identity

B4 no longer assumes every curriculum problem uses the old local catalog ID
shape such as `a693`.

Published Problems may use canonical IDs such as:

```text
CF-1A
CSES-1068
LC-2235
APCS-ZJ-q184
```

The scratch file preserves the Published `placement_uid`.  Control Center
resolves that identity back through `curriculum/published.v23.json`, so a
Finish/Review can create the correct PB/Skill Evidence without inventing a
legacy catalog alias.

The legacy problem-level progress mutation is skipped for these
Published-runtime scratch files.  The durable v2.3 Evidence outbox is the
authoritative local learning mutation.

## Today UX

Today shows both lanes in the same session:

- bounded Adaptive Review;
- protected New Learning capacity.

For New Learning it displays:

- Skill UID and name;
- Unit;
- Path Stage;
- Ready/Learning state;
- current Evidence lower bound;
- prerequisite status;
- why this Skill is next;
- Lesson UID;
- next Placement role and Problem.

If no Skill is currently start-ready, Today shows the first blocked Skill and
the exact prerequisite Evidence gap.

If all Required route Skills have reached the B4 start threshold, Today states
that the **start route** is complete and explicitly does not claim RR/IR
readiness.

## Failure behavior

Missing or malformed Published Curriculum fails closed.

The runtime does not fall back to:

- legacy Tags;
- manual Skill Status;
- title/topic inference;
- relation order;
- stale Notion runtime reads.

Notion remains the authoring SSOT, but Today runs entirely from the reviewed Git
snapshot plus durable learner Evidence.
