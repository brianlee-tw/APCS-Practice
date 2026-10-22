# AI Problem Curation / Testcase QA Contract — pilot v0 (candidate)

This is a **proposed pipeline policy**, not a claim that an AI provider has already been connected. Existing modules define record and verification truth; this document does not introduce another database or source of truth.

## Existing supported entrypoints

| Step | Existing code | Reality |
| --- | --- | --- |
| L0 dedupe / normalized ZeroJudge URLs | \`tools/problem_intelligence.py import\` | Implemented; ZeroJudge only; does not download/verify a problem statement |
| L0 source metadata | \`tools/problem_intelligence.py metadata --input\` | Implemented; source information must be supplied |
| L1 classification | \`tools/problem_intelligence.py classify --input\` | Implemented; validates supplied JSON; **does not call an LLM** |
| L2 teaching package | \`tools/problem_enrichment.py create\` | Implemented; requires supplied content and solution source |
| L2 compile/sample/differential | \`tools/problem_enrichment.py verify-*\` | Implemented, but each receipt has limited authority |
| Test Center assets | \`tools/test_assets.py\` | Implemented; durable \`tests.json\` and runtime Candidate trust states |
| Search and filters | \`tools/problem_library.py smart_search\` | Keyword/filter parser; not semantic embedding retrieval |
| Official verdict | External OJ | Human submits; no automated Judge verdict ingestion |

## Proposed future AI-assisted pipeline

\`\`\`text
Published/Notion reference + official URL
  → source identity + statement/constraints/sample verification
  → human-/machine-checkable source fingerprint
  → AI classification proposal (never authority)
  → deterministic schema validation, contradiction checks, QA triage
  → verified/curated selection
  → AI edge-case proposals (CANDIDATE)
  → oracle or manual source-backed expected-output verification
  → differential / regression + official sample tests
  → durable testcase curation
  → Test Center exposure under spoiler policy
\`\`\`

## Provenance required before accepting an AI proposal

The review receipt should identify source platform and stable external ID, exact original URL, source/statement fingerprint and access status, prompt/template version, model/config identifier, generation time, candidate rationale, ambiguity flags and QA reviewer/decision. It must **not** embed private credentials, copyrighted full problem statements without permission, or raw learner-private data.

Candidate classification fields must use the current \`apply_classification\` schema: Primary/supporting Skills, D1–D5, prerequisite candidates, expected complexity, Role, alternate-solution risk, Evidence suitability, rationale, ambiguity and confidence. The existing 0.80 threshold is an **automatic candidate-screening threshold**, not proof of correctness or permission to publish.

## Testcase trust firewall

- Provenance: \`OFFICIAL\`, \`AI_GENERATED\`, \`MANUAL\`, \`ORACLE\`.
- Trust: \`OFFICIAL\`, \`CANDIDATE\`, \`ORACLE_VERIFIED\`, \`DIFFERENTIAL_VERIFIED\`.
- \`AI_GENERATED\` with an AI-guessed output stays \`CANDIDATE\`. Candidate cannot contribute Test Center PASS/FAIL.
- Official sample requires the actual OJ/source sample, not merely an LLM claim.
- Verified expected output requires a reliable reference/oracle or documented manual proof and replayable test receipt. Compilation and passing samples are not enough.
- No deterministic oracle = candidate remains candidate, even if multiple LLMs agree.
- Strict Transfer/Mock/Exam pre-attempt: only official cases, no hidden testcase inventory, no skill/method spoilers.
- Local PASS ≠ OJ AC ≠ learner Evidence ≠ mastery/readiness.

## QA release gate

A future provider/automation integration must prove:
1. deterministic duplicate matching and correct judge identities;
2. rejection of missing or conflicting constraints;
3. no silent L0/L1/candidate → Published promotion;
4. reproducible source fingerprints and test-generation seeds;
5. output/compile/timeouts, oracle mismatches and errors handled explicitly;
6. strict spoiler and official-case visibility;
7. bounded user cost, minimal required manual input, and safe retry/idempotency;
8. before/after comparison on the first curated 3–5 problems.

Do not implement a generalized crawler, provider abstraction or auto-judge submission until the smaller verified workflow demonstrates benefit.
