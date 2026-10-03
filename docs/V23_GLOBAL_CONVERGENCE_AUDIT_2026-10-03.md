# APCS v2.3 Global Convergence Audit — 2026-10-03

Status: **ENGINEERING CONVERGENCE / LEARNER VALIDATION DEFERRED**

This audit re-reads the current v2.3 authority stack after the Worker #55 production closure and the subsequent learner-runtime feature work. It does not award learner mastery or readiness.

## Authority snapshot

- Notion remains authoring / long-form / Problem Bank / REC / Evidence SSOT.
- Git `main` remains deterministic runtime / compiler / policy / tests / receipts authority.
- VS Code Control Center remains the default learner-facing operational surface.
- Cloudflare remains browser-value runtime + trusted writeback; it must not become a second adaptive-memory authority.
- `LEARNER_READINESS = NOT ASSESSED`.

## Roadmap convergence

| Roadmap item | 2026-10-03 status | Evidence / decision |
| --- | --- | --- |
| Taxonomy granularity audit | **PASS / no split required** | Live Skill Map v3 has 39 unique Skill UIDs, unique Path Order, explicit Reading + Implementation capability on every Skill, and correct Required / Bridge / Extension boundaries. Broad labels remain intentional competency bundles; no demonstrated coverage gap justifies taxonomy expansion. |
| Skill competency definition audit | **PASS** | All 39 Skills have Conceptual Requirement, Implementation Requirement, Recommended Problem Types, Path Stage, Evidence Suitability, 3+3 Relevance and 5+5 Relevance populated. |
| Problem Bank QA convergence | **OPEN — #40, staging only** | Needs-QA staging rows remain fail-closed. PB-179 / PB-180 / PB-181 production-integrity metadata was repaired on 2026-10-03; production system-audit is now clean. Remaining #40 work is content curation and must not be filled by inference merely to reduce counts. |
| Source URL completeness | **PASS for current PB schema** | Live Problem Bank query after PB-11 repair returns zero rows with empty `題目連結`. PB-11 / ZJ-a874 canonical URL was verified and repaired while retaining Needs QA. |
| Multi-solution UX | **PASS** | PR #55: one Problem identity can list/open/add multiple Solution records; Complexity remains bound to actual solution path. |
| README / legacy docs consistency | **PASS in this transaction** | README now reflects Reading runtime, learner status, multi-solution UX and diagnostic-site authority boundary. |
| `site/data/skill-model.v1.json` audit | **PASS / compatibility-only** | Machine-readable `scope=diagnostic-only`, `runtimeAuthority=false`, `readinessAuthority=false`, `canonicalLearningSkillMap=Skill Map v3`. |
| Diagnostic selection quality | **PASS in this transaction** | 5/10/15 remain dimension-balanced; deterministic variants rotate repeat attempts and interleave dimensions instead of always taking the first block. |
| Pre-commit / quality-gate alignment | **PASS in this transaction** | Local full quality gate and GitHub metadata job both run Python runtime regression plus Node diagnostic-site regression. |
| Branch protection / ruleset hardening | **PASS** | Active ruleset `main-production-protection` (ID 24400789): PR required, deletion/non-fast-forward protected, linear history, required checks `metadata` + `changed-solutions`, no bypass actors. |
| Notion schema migration / deprecated field cleanup | **CLOSED** | REC-v3.1 deprecated-property writes were removed in Worker #55; Reading non-judge transport was subsequently verified in Worker #58. Both production receipts remain durable. |
| Cloudflare learner-runtime slimming | **PASS as authority decision; no duplicate state added** | Browser runtime remains semantic lessons/labs/visuals + trusted writeback. Adaptive retention/capacity remains local; do not mirror local Skill × Track memory into Cloudflare/Notion just to populate a dashboard. |
| Dashboard / Evidence / retention / capacity views | **PASS locally** | PR #56 adds Control Center `學習狀態` sourced from durable outbox + derived Skill × Track memory + Today capacity, with explicit non-readiness boundary. |
| Real-use scheduler calibration | **DEFERRED — requires learner evidence** | Memory policy is versioned and rebuildable; calibration without real delayed evidence would fabricate confidence. |
| Learner Experience cognitive-flow refinement | **ENGINEERING SUPPORT COMPLETE; manual acceptance deferred in #32** | Reading response-first flow, track-aware Today, runtime scratch identity, backward-safe Finish/Review, multi-solution UX and learner status are implemented. Genuine learner walkthrough remains required. |
| Delayed / transfer / timed readiness evidence | **DEFERRED — learner activity required** | Engineering must not synthesize A0/delayed/transfer/timed evidence. |
| RR3 / IR3 | **NOT ASSESSED** | Requires designated evidence and readiness gate evaluation. |
| RR5 / IR5 | **NOT ASSESSED** | Same boundary at the later target. |

## Current Git vs production runtime

Cloudflare production is Worker **#58**:

- version: `0eafa60d-6d4d-4edb-b1eb-ac6a9a3625b6`
- deployment: `220994e0-549b-4143-800e-44c089c3ba4a`
- production source authority: `0be65f2ab4ca44ea089aa48afc63ef09afd1778f`

The Reading non-judge transport contract is now production-verified:

- remote Reading attempt may use `Judge Result = N/A`;
- EV-v1 preserves `Track = Reading` and `Judge Result = N/A`;
- REC-v3.1 projects the presentation result to `未提交/未知` rather than fabricating judge success;
- exact retry remains duplicate-safe;
- cleanup restored canonical counts to REC=137 / EV=0;
- production system-audit is clean with 0 exceptions and 0 warnings.

The direct Version URL gate was waived only after candidate and random nonexistent aliases produced the same Cloudflare 404/1042 router fingerprint; exact application QA then passed through candidate@0 + production-host version override before promotion.

## Remaining work that cannot be truthfully completed by engineering alone

1. **#40 Problem Bank staging QA** — content classification requires reliable source/placement evidence; missing metadata must not be guessed.
2. **#32 genuine learner validation** — requires an actual learner walkthrough, real Published Curriculum attempt and end-to-end ACK verification.
3. **Scheduler calibration / readiness** — requires real delayed / transfer / timed evidence.

Everything else in this roadmap should be treated as engineering closure or compatibility maintenance, not a reason to create a second taxonomy, scheduler, dashboard authority or learner-state SSOT.
