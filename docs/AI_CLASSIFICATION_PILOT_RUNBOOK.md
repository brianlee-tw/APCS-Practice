# AI Candidate Classification Lane — 4-item controlled pilot

**Status:** implemented candidate generation/QA tooling, NOT a learner-facing feature, not Published, and not automatically connected to a paid model. PR #89 remains Draft.

## What this implements

\`tools/ai_candidate_pipeline.py\` provides three bounded subcommands.

\`\`\`text
Reviewed ZeroJudge L0 metadata (4 items)
  │
  ├─ prepare → deterministic jobs with SHA-256 source fingerprints
  │              + published 39-Skill vocabulary (not answer labels)
  │
  ├─ generate → OPTIONAL explicit OpenAI Responses API
  │              + structured JSON Schema
  │              + 4 items maximum, no background execution
  │              + results recorded as AI_CANDIDATE only
  │
  └─ evaluate → deterministic identity, fingerprint, taxonomy and
                 Published Skill/Difficulty/Role disagreement checks
                 → CANDIDATE_UNREVIEWED / NEEDS_QA / NOT_GENERATED
                 → QA JSON report only; never modifies L0/L1 / Notion
\`\`\`

The default is to **not** spend money or send anything to an external model. \`prepare\` and \`evaluate\` are offline. \`generate\` requires the operator to supply a model, local \`OPENAI_API_KEY\`, and \`--confirm-api-cost\`.

## Safe operator commands (WSL / Linux)

Run in repository root on PR branch (after \`git fetch\`); do not apply to \`main\` implicitly.

\`\`\`bash
mkdir -p .apcs/runtime/ai_classification

python3 tools/ai_candidate_pipeline.py prepare \
  --output .apcs/runtime/ai_classification/jobs.json
\`\`\`

To use an external paid API, separately authorize billing. ChatGPT subscription access is **not** the same thing as API credentials/billing.

\`\`\`bash
read -rs -p 'OpenAI API key: ' OPENAI_API_KEY
echo
export OPENAI_API_KEY

python3 tools/ai_candidate_pipeline.py generate \
  --jobs .apcs/runtime/ai_classification/jobs.json \
  --output .apcs/runtime/ai_classification/responses.json \
  --model gpt-4.1-mini \
  --confirm-api-cost

unset OPENAI_API_KEY
\`\`\`

Then perform deterministic, offline QA:

\`\`\`bash
python3 tools/ai_candidate_pipeline.py evaluate \
  --jobs .apcs/runtime/ai_classification/jobs.json \
  --responses .apcs/runtime/ai_classification/responses.json \
  --output .apcs/runtime/ai_classification/qa.json
\`\`\`

Outputs are **local runtime candidates**; they do not enter Notion, Published Curriculum, \`data/problem_intelligence\`, \`data/problem_enrichment\`, Test Center trust, or Evidence. To regenerate without overwriting an earlier receipt, use distinct output filenames. No credentials or personal learner data should be committed.

## Model and QA guardrails

The provider path uses \`POST https://api.openai.com/v1/responses\`, fixed HTTPS host, \`store:false\`, strict Structured Outputs, and no executable model-supplied code. Only public source-derived metadata and allowed Skill/role vocabularies are sent (no learner attempts, credentials, local files or full copyrighted statements).

The model must not invent missing constraints. Candidate data must match the prepared source identity and SHA-256. \`evaluate\` rejects duplicates, unknown Skill UIDs, unsupported role/difficulty, unexpected JSON fields (including a forged \`published\` property), changed source metadata, and wrong source ID.

An otherwise well-formed model proposal goes to \`NEEDS_QA\` if confidence is below 0.80, essential fields are empty, method ambiguity is reported, or its Skill/Difficulty/Role disagrees with the existing Published record. Agreement and high confidence produce only \`CANDIDATE_UNREVIEWED\`, **never Verified or Published**.

**Limitation:** these four L0 records store short extracted source summaries, not entire source statements. Model output is a starting hypothesis, not authoritative proof of problem interpretation, exact constraints, reference correctness, or APCS suitability. A reviewer must check the official original problem before any further L1 adoption or L2/testcase enrichment.

## Current completion and next gate

- Completed: source-backed 4-item work queue, optional model adapter, schema-bound response, provenance & deterministic QA, synthetic API mocks, and regression guards.
- Not done: running a paid API on behalf of the learner (requires explicit operator credentials/cost consent), accepting/classifying any L1 entry from AI, generating official cases from AI, or publishing any new placement.
- Next: inspect first actual 4 AI replies with the learner, correct systematic classification mistakes, then decide whether to add an explicit review-controlled L1 adoption command. Do not turn this into an unattended large-scale ingestion service before real QA.
