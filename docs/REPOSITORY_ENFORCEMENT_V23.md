# APCS Repository Enforcement v2.3

Status: **Phase 2A target contract**

This document defines the repository-level policy for `main`.  It is separate
from learner readiness and curriculum semantics.

## Why this exists

The repository already follows:

```text
branch
-> local quality gate
-> pull request
-> APCS Validate
-> merge
-> post-merge validation
```

Without a GitHub ruleset, that sequence is convention rather than enforcement.

## Canonical local gate

```bash
python3 tools/quality_gate.py
```

The pre-commit hook and Control Center commit flow both use this command.

It includes:

1. full Python regression tests;
2. unstaged + staged `git diff --check`;
3. Catalog / learning-data validation;
4. known-warning budget.

`python3 tools/apcs.py validate` is a narrower diagnostic command and is not
the commit acceptance gate.

## Required GitHub ruleset

Create one **branch ruleset** targeting only `main`.

Recommended name:

```text
main-production-protection
```

Enforcement:

```text
Active
```

Rules:

- Restrict deletions.
- Block force pushes.
- Require linear history.
- Require a pull request before merging.
- Required approvals: 0.
- Require status checks to pass before merging.
- Required status checks:
  - `metadata`
  - `changed-solutions`
- Do not add a broad bypass actor.

Do **not** require:

- `sync` — this runs after a push to `main`;
- `validate-site` globally — the site workflow is path-conditional.

For this solo repository, CI is the merge gate; review approval is not used as
a substitute for validation.

## Verification

After enabling the ruleset:

1. repository rulesets should list `main-production-protection` as Active;
2. `main` should report protected/enforced;
3. a direct unsafe push to `main` should be rejected by GitHub;
4. a pull request with both required checks passing should remain mergeable;
5. squash merge remains the normal merge path.

Do not intentionally create or push destructive content merely to test
protection.  A harmless temporary branch / no-op direct-push probe is enough if
GitHub UI state is otherwise ambiguous.

## Boundaries

This policy does not change:

- Published Curriculum;
- Skill / Problem identity;
- Evidence / MEAS semantics;
- Remote Writeback;
- `LEARNER_READINESS`.

It only makes the engineering release path fail closed.
