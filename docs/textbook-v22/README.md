# Paper companion v2.2

The five-volume paper edition links to the existing 52 lessons, 39 skills and Problem Bank. `crosswalk.json` contains actual local PDF pages and reference links. It contains no progress, mastery, benchmark answers or gate decisions. The paper edition number is independent of runtime v2.3/v2.4.

Notion reference: https://app.notion.com/p/40143be958cd81398dc0c60e560a394e

## Validation

From the repository root:

```sh
node tests/textbook_v22_reference.mjs
node tests/textbook_v22_worker_isolation.mjs /tmp/worker-isolation-v22.json
python -m unittest discover -s tests -q
```

The reference check compares all 52 Notion routes and 39 skill classifications with the existing Git authority. It validates 56 reference rows and 71 lesson-skill relations without changing the curriculum.

The Worker test imports the operational Worker unchanged and replaces its Notion transport with a closed in-memory implementation. Unexpected calls throw. It covers Guided, Independent, Transfer, Assisted Debugging, Delayed Retest, Timed, WA/CE/RE/TLE/AC, Reading N/A, Python language preservation, exact-retry duplicate suppression and inconsistent assistance rejection. No request reaches a live database. Valid for Gate remains false; Skill mastery is never written.

## Release limits

This branch does not deploy a Worker, change MEAS-v1, convert historical REC into EV, or alter RM/IM. Remote Measurement to Review Due and a genuine learner pilot still require a safe authorized environment and real evidence. Formal C-form RR3/RR5 remain fail-closed pending production and sealing acceptance. Python transfer results must not be inferred as C++17 mastery; EV has no separate language field in the current schema.

Notion's stale C1 summary was replaced with a qualified reference to Git C8 authority. All 52 lessons received a short Paper Companion reference. The C-reading bridge/practice and MIX-02 novelty warning were updated and read back. No formal item was accessed or republished. REC and EV counts remained 137 and 0.

Rollback: revert this branch's reference/test additions. For Notion, remove only the exact added Paper Companion blocks and C-reading alignment sections; restore the saved original authority callout if reverting it. Preserve all pre-existing content, native children, records and benchmark settings. This publication does not assert Production Ready.
