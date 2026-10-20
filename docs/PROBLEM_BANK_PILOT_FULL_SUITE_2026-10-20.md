# Stage J: Verified Full Suite preview (2026-10-20)

PR: #89 (Draft, unmerged). No API key or paid model calls.

## Scope
Four previously source-reviewed Published exercises retain 5 official FAST samples. This stage adds 17 AI-designed FULL-only testcases with differential verification:

| PB UID | Official FAST | New FULL edges |
| --- | ---: | ---: |
| PB-42 / CSES 1069 | 1 | 4 |
| PB-150 / CSES 1094 | 1 | 5 |
| PB-97 / CF 71A | 1 | 3 |
| PB-120 / APCS q836 | 2 | 5 |

All new cases: provenance AI_GENERATED; trust DIFFERENTIAL_VERIFIED; suite full; visibility practice. Neutral display names protect A0 independent attempts. No AI output was relabelled as OFFICIAL.

## Independent evidence

CI regression: tests/test_pilot_preview_edge_cases.py.

Two distinct Python routes/problem:
- Repetitions: streaming run-count vs regex run extraction.
- Increasing Array: running maximum vs prefix-max accumulation.
- CF 71A: branching per word vs independent string transformation.
- q836: step-by-step jump simulation vs next-trap-event stepping.

Each stored edge output and each official sample is checked against both references. Additional deterministic fuzz: 240 valid inputs per problem, 960 total (seed 20261020). Constraint checks: CSES 1069 length 1e6, CSES 1094 n=200000 including sum > signed 32-bit, CF 71A 100 words of length 100, and q836 trap periods across x1,x2=1..10.

Differential agreement is NOT external OJ acceptance, proof for all hidden cases, or learner mastery.

## Preview and release

Manifest: data/problem_pilot/workbench_preview.v1.json tracks official_count separately from verified_edge_count. The read-only tools/pilot_workbench_preview.py verifies each judge identity, sample source, trust state, and Fast/Full isolation. tools/pilot_release_preflight.py tracks 13 official samples across 8 Test Center problems, plus 34 distinct differential edge cases.

Practice Fast: official only.
Practice Full: official + validated edges.
Exam/Transfer preattempt: official only.
Exam/Transfer postattempt: Full repair possible.

Release remains BLOCKED_MANUAL. C8 OPEN; learner readiness NOT_ASSESSED; Notion and Published unchanged. A real user VS Code session remains pending. No merge or evidence writeback.

CI #333 PASS on code/test head a742cc3b018ddf18b3d48f5cbb1ad3a87b18ae29.
