# ChatGPT 對話式分類｜題庫 Pilot Runbook

**Current policy (2026-10-18): ChatGPT chat is the AI worker. No API key, API billing, model call or provider receipt is required.**

## Authority and scope

- Work branch: `feat/problem-bank-pilot-20261018`; PR #89 remains Draft and must not be automatically merged.
- Canonical Published snapshot and Notion Problem Bank are unchanged.
- Exactly four official-page-reviewed ZeroJudge L0 source profiles are in scope: d097, d732, j606, d067.
- `data/problem_pilot/chatgpt_proposals.v1.json` holds **ChatGPT-authored AI Candidate classifications**. They are not human-approved.
- Prompts/AI outputs are not learner Evidence, official testcase output, verified algorithms, hidden OJ AC, or permission to publish.

## Workflow: ChatGPT → Candidate JSON → offline QA

```text
Read official problem page + compare Published baseline
  → ChatGPT drafts PB UID + candidate JSON (no source-fingerprint claim)
  → commit/edit data/problem_pilot/chatgpt_proposals.v1.json on the PR branch
  → tools/ai_candidate_pipeline.py review-chatgpt
  → code attaches trusted job identity + SHA256 source fingerprint
  → validate Skill IDs, requirements, Published disagreements and ambiguity
  → output QA receipt locally, without modifying Published/Notion/L0/L1
```

The ChatGPT input format has an envelope with `schema_version=apcs-chatgpt-classification-proposals-v1`, `prompt_version=apcs-l1-candidate-v1`, `proposal_source=CHATGPT_CONVERSATION`, `authored_on` (ISO date), `model` (chatgpt-prefixed), and `proposals` (one to four `{pb_uid,candidate}` records). The model does not self-assign a source hash or approval.

## Run only on the PR branch (WSL/Linux)

First check `git status --short --branch`; preserve any unrelated local learner modifications. After safely obtaining the PR branch:

```bash
python3 tools/ai_candidate_pipeline.py review-chatgpt \
  --proposals data/problem_pilot/chatgpt_proposals.v1.json \
  --output .apcs/runtime/ai_classification/chatgpt-qa-01.json
```

**No `OPENAI_API_KEY`, `--model` or `--confirm-api-cost` are used here.** Do not commit `.apcs/runtime/` or rerun using an existing output path (the tool refuses overwrite).

Expected first-batch deterministic QA from the four proposals:

| Problem | Proposed Primary Skill | Proposed D / Role | Expected QA |
| --- | --- | --- | --- |
| d732 / PB-27 | S10_Binary_Search | D2 / Guided Drill | `CANDIDATE_UNREVIEWED` |
| d097 / PB-183 | S05_Array | D2 / Core Independent | `CANDIDATE_UNREVIEWED` |
| j606 / PB-9 | S34_Matrix_2D | D3 / Core Independent | `NEEDS_QA` (string/simulation/matrix representation ambiguity and confidence below 0.80) |
| d067 / PB-182 | S02_Conditionals | D2 / Core Independent | `CANDIDATE_UNREVIEWED` |

`CANDIDATE_UNREVIEWED` means **no hard inconsistency was detected**, not human approval or teaching readiness. QA never sets runtime eligibility or verifies a reference implementation.

## How to add more ChatGPT work without API

1. Select a target already in Published and check official source URL, constraints and samples. Do not accept guessed data or bulk-reproduce copyrighted statements.
2. Add only source-reviewed L0 inputs with stable problem identity. Never invent a source SHA; the offline converter calculates it from the actual local L0 profile.
3. In this conversation, have ChatGPT propose a classification. Keep it in structured `AI_CANDIDATE` form with honest confidence and explicit ambiguities.
4. Run `review-chatgpt`, inspect `NEEDS_QA` flags, then separately request human review of problematic mappings.
5. Only after review consider explicit adoption into L1 or generation of candidate edge tests. AI-produced expected output **never** counts as an OFFICIAL testcase or VERIFIED correctness.

## Legacy provider option

The earlier optional `generate` command remains in the source for compatibility but **is not part of this user's workflow**. This stage did not call a paid model API and no API key is necessary. Do not use this path unless the user explicitly reverses the no-API decision.

## Regression and release

- `python3 -m unittest tests.test_ai_candidate_pipeline -v`
- `python3 -m unittest discover -s tests -v`
- `python3 tools/pilot_coverage.py`
- C8 remains OPEN; learner readiness remains NOT_ASSESSED.
- The Draft PR must not be merged on the basis of CI alone.
