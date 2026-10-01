# Notion Core Field Audit for APCS v2.3

Status: **Gate 0 working audit**

This audit treats the current Notion system as valuable input, not unquestionable truth. No learner data is mutated by this document.

## 1. Live-state findings

Observed during the v2.3 audit:

- Skill Map: 39 Skills.
- RM populated: 0 / 39.
- IM populated: 0 / 39.
- Evidence Ledger: 0 rows.
- Skill Status is nevertheless populated across Learning / Practice / Ready / Locked.
- Problem Bank: 181 rows.
- Active Problem Bank rows: 131.
- Needs QA: 50.
- Active rows missing Skill: 3.
- Active rows missing calibrated Difficulty: 3.
- Active rows missing Primary Lesson: 6, including Mock rows where no lesson placement may be legitimate.
- Solve Records: 137 rows.
- Formal learner Solve Records observed in the aggregate audit: 0.
- System-test Solve Records observed: 71.
- Most existing REC rows are therefore not yet usable as a trustworthy learner mastery history.

The immediate consequence is that existing Skill Status values cannot be treated as measured learner state while Evidence is empty.

## 2. Classification vocabulary

- **KEEP**: valuable authored or durable data remains in Notion.
- **DERIVE**: value should be computed from other authoritative facts.
- **MOVE TO GIT**: executable/version-sensitive machine rule should live in the published Git contract.
- **SYSTEM-MANAGED**: retained in Notion but written by the integration, not manually maintained.
- **DELETE**: field is redundant or actively misleading once migration is complete.
- **ARCHIVE**: keep only for historical/audit value, outside the active learner workflow.

## 3. Skill Map v3

| Field | Decision | v2.3 treatment |
|---|---|---|
| Skill UID | KEEP | Stable identity; author in Notion, publish to Git snapshot. |
| 技能 | KEEP | Human-readable Skill name. |
| 課程單元 | KEEP | Curriculum placement authored in Notion and compiled. |
| CL | KEEP | Curriculum depth, not learner mastery. |
| 能力面向 | KEEP | Reading / Implementation applicability. |
| 前置技能節點 | KEEP | Authoring relation; compiler validates references and cycles. |
| Path Stage | KEEP | Learner route metadata. |
| Path Order | KEEP | Display/route order only; prerequisite relation remains structural truth. |
| 3+3 Relevance | KEEP | Curriculum calibration. |
| 5+5 Relevance | KEEP | Curriculum calibration. |
| Conceptual Requirement | KEEP | Human-readable teaching contract. |
| Implementation Requirement | KEEP | Human-readable teaching contract. |
| Recommended Problem Types | KEEP | Authoring guidance. |
| Evidence Suitability | KEEP | Authoring guidance; executable gate semantics belong in Git rules. |
| Gate Override / Notes | KEEP | Human note only; must not silently override runtime. Any executable override requires a reviewed Git contract change. |
| 題庫題目 | SYSTEM-MANAGED | Relation view; do not manually maintain as an independent truth. |
| Evidence Events | SYSTEM-MANAGED | Backlink from Evidence Ledger. |
| RM | DERIVE | Computed from valid Evidence + versioned gate rules. |
| IM | DERIVE | Computed from valid Evidence + versioned gate rules. |
| Skill Status | DERIVE | Computed from prerequisites, evidence, current learning activity, and review state. Existing manual values are not mastery evidence. |
| Reading Milestone | DERIVE | Navigation alias from readiness/gate state; not manually authored learner truth. |
| Implementation Milestone | DERIVE | Same as above. |

### Required schema refinement

The current 39-Skill model mixes:
- concepts/techniques;
- bundled families;
- cross-cutting competencies.

Gate 3 must review these separately. In particular, `S39 Program Tracing / Debugging / Testing` must not be assumed to be one indivisible ability.

## 4. Problem Bank v3

| Field | Decision | v2.3 treatment |
|---|---|---|
| PB UID | SYSTEM-MANAGED | Stable Notion identity. |
| Problem ID | KEEP | Stable external/problem identity. |
| 題目 | KEEP | Human-readable title. |
| 來源平台 | KEEP | Intrinsic provenance. |
| 作答平台 | KEEP | Judge/runtime target. |
| 題目連結 | KEEP | Canonical judge/source link. |
| 難度（D1–D5） | KEEP | Calibrated instructional difficulty; never user-perceived difficulty. |
| Exam Band | KEEP | Assessment calibration. |
| 3+3 Suitability | KEEP | Curriculum calibration. |
| 5+5 Suitability | KEEP | Curriculum calibration. |
| Alternate Solution Risk | KEEP | Useful for evidence interpretation. |
| Calibration Notes | KEEP | Human authoring notes. |
| 訓練目的 | KEEP | Human teaching intent. |
| 技能節點 | KEEP, MIGRATE | Replace undifferentiated multi-relation semantics with Primary Skill + Supporting Skills at published-contract level. |
| 題目角色 | KEEP, MIGRATE | Role belongs to a Placement/Activity, not permanently to the problem. Migrate out of intrinsic problem metadata. |
| Primary Lesson | KEEP, MIGRATE | Move into Placement entity. Mock/benchmark items may legitimately have no Lesson placement. |
| Lesson Order | KEEP, MIGRATE | Move into Placement entity. |
| Record Prompt Ready | DERIVE | Runtime readiness should be generated from placement/runtime support, not maintained as a separate authoring checkbox. |
| Placement QA | SYSTEM-MANAGED | Compiler/validator result. Manual PASS must not override missing required metadata. |
| 教材狀態 | KEEP, REDESIGN | Replace loose Active/Needs QA semantics with explicit Draft / Published / Retired lifecycle. Only Published enters runtime snapshot. |
| 解題紀錄 | SYSTEM-MANAGED | Backlink only. |
| Evidence Events | SYSTEM-MANAGED | Backlink only. |

### Publish invariant

A Problem/Placement cannot enter the published runtime with missing fields that are required for its role.

For example, a Mock may omit Primary Lesson, but cannot be Published with unknown Skill or Difficulty if the scheduler/evidence engine requires them.

## 5. Solve Record REC-v3.1

REC should represent one immutable attempt story, not a mutable scheduling object.

| Field | Decision | v2.3 treatment |
|---|---|---|
| REC UID | SYSTEM-MANAGED | Stable record identity. |
| Writeback ID | SYSTEM-MANAGED | Idempotency key from VS Code/outbox. |
| 題目 | DERIVE | Human display title derived from Problem relation/identity. |
| 題庫題目 | SYSTEM-MANAGED | Canonical relation. |
| PB UID | DERIVE | Readable projection from related Problem. |
| Problem ID | DERIVE | Readable projection from related Problem. |
| 來源平台 | DERIVE | Projection from Problem Bank. |
| 作答平台 | DERIVE | Projection from Problem Bank / actual judge if overridden explicitly. |
| 題目連結 | DERIVE | Projection from Problem Bank. |
| 難度（D1–D5） | DERIVE | Projection from Problem Bank placement/calibration. |
| 練習日期 | SYSTEM-MANAGED | Notion row creation time; retained for compatibility, not used as exact offline attempt time. |
| Attempt Finished At | SYSTEM-MANAGED | Exact timezone-aware attempt completion timestamp from the durable outbox; added for offline/retry correctness. |
| 使用語言 | KEEP | Attempt fact. |
| 最新提交結果 | KEEP | Attempt fact. |
| Assistance | KEEP | Attempt fact; unknown remains blank. |
| 獨立完成 | KEEP | Attempt fact. |
| 嘗試次數 | KEEP | Attempt fact. |
| 解題時間(分鐘) | KEEP | Attempt fact. |
| 錯誤類型 | KEEP, REDESIGN | Preserve root-cause taxonomy, but separate coarse error family from C1-C11 decision-process codes if needed. |
| 核心收穫 | KEEP | Human reflection. |
| 紀錄來源 | SYSTEM-MANAGED | HTML Direct / VS Code Direct / Coach Direct / Manual Notion / Legacy, generated by the write path. |
| 紀錄性質 | SYSTEM-MANAGED | Formal / Test / Legacy; tests must never enter learner evidence. |
| 技能節點 | SYSTEM-MANAGED | Context relation derived from Placement and actual observed target; not manually copied from all Problem tags. |
| Evidence Events | SYSTEM-MANAGED | Backlink. |
| 學習階段 | DERIVE | Prefer explicit Activity/Role in attempt context; avoid overlapping subjective state. |
| 進度狀態 | DELETE | A completed immutable attempt should not also act as a mutable task/status object. |
| 複習日期 | DELETE | Scheduling belongs to adaptive Skill x Track engine, not to an individual REC. |
| 學習歷程候選 | KEEP | Optional portfolio signal, independent from mastery. |
| 學習歷程證據 | KEEP | Optional human-readable portfolio note. |

## 6. Evidence Ledger v1

One Evidence row should mean one observable claim about one **Skill x Track**.

| Field | Decision | v2.3 treatment |
|---|---|---|
| EV UID | SYSTEM-MANAGED | Notion human-facing auto-increment identity. |
| Event ID | SYSTEM-MANAGED | Stable remote idempotency identity from the durable outbox; retries must reuse the same EV row. |
| 日期 | SYSTEM-MANAGED | Event timestamp. |
| Track | KEEP | Reading / Implementation. |
| Activity | KEEP | Concept Check / Guided / Core / Transfer / Review / Diagnostic / Mock. |
| Outcome | KEEP | PASS / PARTIAL / FAIL. |
| Judge Result | KEEP | Optional implementation outcome. |
| Accuracy % | KEEP | Optional reading/assessment measure. |
| Assistance | KEEP | Evidence-quality fact. |
| Independent | KEEP | Evidence-quality fact. |
| Timed | KEEP | Evidence-quality fact. |
| Time min | KEEP | Workload/evidence fact. |
| Novelty | KEEP | New / Seen / Delayed Retest / Transfer / Mixed / Same Problem Repeat. |
| Skill | SYSTEM-MANAGED | Exactly one evaluated Skill per event in v2.3. |
| Problem | SYSTEM-MANAGED | Optional source Problem relation. |
| Solve Record | SYSTEM-MANAGED | Source attempt relation. |
| Evidence Note | KEEP | Concise interpretation. |
| Delay Days | DERIVE | Compute from timestamps and prior qualifying evidence; do not manually enter. |
| Valid for Gate | DERIVE | Deterministic result of versioned MEAS rules, not a manual checkbox. |

## 7. Specification pages

### TAX / MEAS / Current Route

Current Notion pages contain both:
- valuable rationale and human-readable definitions;
- executable machine rules.

Decision:
- **KEEP** rationale, examples, learner explanations in Notion.
- **MOVE TO GIT** executable gate logic, scheduler policy, publish invariants, and machine-enforced enums.
- **DERIVE** dashboards and Current Route from published curriculum + evidence.

The published Git contract becomes the runtime contract. Notion remains the authoring/explanation surface.

## 8. Hosted Workspace / Cloudflare

Decision:
- **KEEP** interactive visualizations and labs where browser interaction materially improves understanding.
- **KEEP** writeback API and read-only dashboards where useful.
- **DELETE/RETIRE FROM DAILY FLOW** duplicate code-solving/runtime steps that VS Code can perform better.
- **ARCHIVE** historical release receipts and superseded UI-version closure pages outside the learner route.

## 9. Immediate blockers before Notion mutation

Do not perform destructive migration yet.

First implement:
1. published architecture contract;
2. validator/compiler boundary;
3. replacement VS Code paths for fields marked DELETE/DERIVE;
4. idempotent event/outbox design;
5. readback/reconciliation tests.

Only after these pass should Notion fields be removed or converted.

