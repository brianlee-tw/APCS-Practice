# site/｜Standalone Diagnostic Compatibility Surface

Status: **DIAGNOSTIC ONLY / NON-AUTHORITATIVE FOR v2.3 LEARNING STATE**

This static site is a small anonymous APCS/C++ diagnostic experience. It is intentionally separate from the v2.3 learner runtime.

## What it may do

- serve 5 / 10 / 15 question diagnostic sets;
- score only the questions answered in that diagnostic session;
- show descriptive dimension scores and wrong-answer review;
- provide deterministic next-step recommendations inside the diagnostic product.

## What it must not do

It must **not** be treated as authority for:

- Published Curriculum;
- Skill Map v3;
- Skill × Track adaptive memory;
- REC-v3.1 / EV-v1 durable learner evidence;
- RM / IM / RR / IR;
- mastery;
- APCS readiness.

The file `site/data/skill-model.v1.json` is therefore a **diagnostic display model only**. Its contract must keep:

```json
{
  "scope": "diagnostic-only",
  "readinessAuthority": false
}
```

It is not a stale alternate copy of Skill Map v3 and must never be imported into the v2.3 Control Center as learning-state truth.

## Selection policy

The diagnostic bank currently contains exactly three questions for each of five diagnostic dimensions.

`selectBalancedQuestions(...)`:

- keeps 5 / 10 / 15 modes exactly balanced across the five dimensions;
- deterministically rotates variants on repeat attempts instead of always taking the first rows;
- interleaves dimensions rather than showing one dimension as a block;
- does not turn diagnostic scores into readiness evidence.

## Validation

Both local quality-gate and GitHub CI execute:

```text
node --test site/tests/engine.test.mjs
```

Python v2.3 authority tests also verify that this surface remains explicitly diagnostic-only.
