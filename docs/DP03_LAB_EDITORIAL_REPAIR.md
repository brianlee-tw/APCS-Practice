# DP03 direction Lab repair

On 2026-10-23 the live `dp03-iteration-direction-stepper` displayed a generic
state-definition question and generic Next steps. Its promised ascending /
descending comparison and knapsack state were absent. The paper lesson is
correct; the interactive handoff is incomplete.

The canonical Worker now curates this one existing Lab route. The model uses
one item `(w=2,v=3)` and exact capacity `W=4`, with a distinct unreachable value.
Learners predict first, step through descending 0/1 updates, then locate the
illegal reuse in ascending updates. Stable Lesson, Skill and route identities
remain unchanged. A content revision isolates local completion from the old
placeholder. No REC/EV, learner Mastery or measurement API is called.

Validation from base `c0362c19457f7bb230c615b218f2c310ea602cf5`:

```sh
python3 -m unittest discover -s tests
node tests/dp03_lab_curation.mjs
node tests/premium_worker_isolation.mjs /tmp/rec-ev-isolation.json
```

- 484 Python regressions pass.
- 72 independent subset-oracle cases and 3 canonical Worker route cases pass.
- 13 in-memory REC/EV scenarios pass, including duplicate retries, assistance,
  verdicts and Python language preservation; no Production writes occur.
- Other Lab response remains byte-identical in the route regression.
- Immutable recovery assets are not edited.

Deployment: **NOT DEPLOYED**. Candidate browser acceptance, preview and
Cloudflare production-control-plane verification remain required. Publication
QA does not close C8, formal C-form sealing or live Measurement / Review Due.
Follow the existing `CURRENT_AUTHORITY` safe-release process; do not promote this
branch simply because software tests pass. Rollback is the previous deployed
version; if merged, reverting this isolated commit removes curation.
