# APCS Problem Bank Pilot | Stage K: CF 977C Semantic Checker

Date: 2026-10-22 (Asia/Taipei)
Branch/PR: feat/problem-bank-pilot-20261018 / PR #89 (Draft, NOT merged)
Engineering status: APCS Validate #345 PASS
Release state: BLOCKED_MANUAL, C8 OPEN, Learner Readiness NOT_ASSESSED

## Official judge contract

Source: https://codeforces.com/problemset/problem/977/C

CF 977C / PB-109 is an any-valid-output task. Input: n, k, then n integers (1<=n<=200000, 0<=k<=n, 1<=a_i<=1e9). A program may output ANY integer x in [1,1e9] for which exactly k of the values are <= x. It must output -1 ONLY when no such x exists. Duplicate values are allowed. In the first official sample x=5 and x=6 are both valid. Ordinary exact comparison with the sample answer 6 would incorrectly reject x=5.

## Engineering changes

- tools/semantic_checkers.py: pure semantic verifier for a single registered mode, CF_977C_ANY_X. Rejects illegal x, incorrect count, impossible/possible -1 confusion, malformed output, incorrect input lengths and out-of-range values. A helper dispatch never falls back to exact output for unknown modes.
- tools/test_assets.py: adds an optional checker field to TestCase (default EXACT) and a bundle-level checker declaration. The semantic mode is authorized **only** for the exact source/codeforces/977C/canonical URL identity. All other sources must remain EXACT. Codeforces 977C must explicitly declare its semantic mode; accidental omission fails closed.
- tools/local_test_runner.py: uses semantic verification only when a registered TestCase checker mode is present. The old exact-output behavior for every other task remains unchanged. Existing timeout, crash and output-size gates are not bypassed.
- tools/vscode_task.py: adds a single exact Published PB/URL allowlist for PB-109 and displays a legal-answer rule rather than an incorrect "expected 6" requirement. It suppresses misleading unified-diff output for semantic tasks.
- data/problem_enrichment/codeforces/977C/tests.json: 2 genuine OFFICIAL Fast examples; 7 ChatGPT-designed AI_GENERATED/DIFFERENTIAL_VERIFIED Full cases covering k=0 feasible/impossible, k=n, 1e9 limit, duplicate-boundary impossibility, and multiple valid outputs.
- data/problem_pilot/workbench_preview.v1.json: explicit five-problem preview inventory, bound semantic mode, official counts and independently verified edge counts.
- tools/pilot_workbench_preview.py and integration/regression tests now reject checker/source mismatch and incorrect sample outcomes. Existing release preflight remains engineering-only and BLOCKED_MANUAL.

## Independent test evidence

tests/test_pilot_semantic_cf977c.py checks:
- Official sample #1: both 5 and 6 return PASS semantics; 7 and -1 rejected.
- Official sample #2: -1 accepted; a numeric output rejected.
- Full tests including k=0, k=n, repeats, 1e9 value/range, incorrect -1, malformed output.
- 400 reproducible random small cases with all potential outputs cross-checked against an independent brute-force enumeration of x.
- Maximum constraint n=200000, with duplicate ranks and valid wide solution interval.
- Wrong URL, judge source, problem identifier or omitted checker cannot enable semantic verification.
- Real C++17 compiled through the existing safe local runner, passing two official and seven Full cases; independent C++ output 5 passes the first official sample despite differing from official illustrative output 6.
- Workbench Published identity -> TestAssetStore -> Exam/Practice Fast/Full and preattempt spoiler checks.
- Semantic UI text explains nonunique acceptable answers and avoids false expected-vs-actual diff.

## Pilot totals at this stage

- 18 PB seed records across the coverage audit (not all are runnable).
- 9 Test Center preview exercises: 4 original ZeroJudge, 4 Stage I multi-judge fixed-output, and CF 977C semantic.
- 15 official Fast sample cases (8 + 5 + 2).
- 41 differential-verified Full cases (17 + 17 + 7).
- No new Notion or Published Curriculum classification; no external OJ submission or real learner Evidence.
- No OpenAI API / API key; ChatGPT authored the problem-specific candidates in conversation.
- Actual user Windows/WSL VS Code C8 learner acceptance is still pending.
- PR #89 remains Draft/unmerged, main unchanged. Automation must never promote these local checks to mastery.

## Outstanding work

Do not extend semantic checking indiscriminately to other tasks. Any future special checker must provide an explicit official judge contract, verified source identity, conservative output validation, independent negative tests, a recorded trust boundary and a separate learner acceptance gate. Keep Custom tasks and q182 source gap unadopted until authoritative source/rubric issues are resolved.
