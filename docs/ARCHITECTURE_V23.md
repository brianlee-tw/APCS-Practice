# APCS Learning System v2.3 Architecture Contract

狀態：**歷史架構契約｜v2.3 已完成並投入 Production**

> 本文件記錄 v2.3 的架構設計與不變條件，不再代表目前開發階段。現在的正式狀態請以 `docs/CURRENT_AUTHORITY.json` 為準；v2.4 的產品與架構契約請見 `docs/V24_PRODUCT_ARCHITECTURE_CONTRACT.md`。

<!-- APCS_CURRENT_AUTHORITY_START -->
## 目前正式狀態（自動產生）

> 本區塊由 `docs/CURRENT_AUTHORITY.json` 產生；不要手動修改。

- 穩定學習執行環境：**v2.3**，狀態 `PRODUCTION_CLOSED`。
- 下一版本：**v2.4**，目前階段 **C4｜認知編排器與 Today v2**。
- 正式課程：**52 Lessons / 14 Units / 39 Skills**；未有真實 Evidence 前不擴張主線。
- Production Worker：**#58 @100%** `0eafa60d-6d4d-4edb-b1eb-ac6a9a3625b6`；system-audit = **PASS_CLEAN**；Preview / Version URLs = **DISABLED**。
- 日常主要介面：**VS Code Control Center**。
- 學習準備度：`LEARNER_READINESS = NOT_ASSESSED`。
- v2.4 正式契約：[`docs/V24_PRODUCT_ARCHITECTURE_CONTRACT.md`](./V24_PRODUCT_ARCHITECTURE_CONTRACT.md)。
<!-- APCS_CURRENT_AUTHORITY_END -->

以下內容保留作為 v2.3 的歷史設計依據。

## 1. Product goal

The system exists to make the learner measurably better at APCS/C++ while keeping daily operation simple and long-term maintenance bounded.

The default daily experience is:

```text
VS Code Control Center
  -> today's route
  -> learn / practice / review
  -> code / build / debug
  -> finish attempt
  -> evidence capture
  -> next action
```

Notion remains important, but it is not the daily runtime.

## 2. System roles

### Notion

Use for:
- curriculum authoring;
- long-form lessons and mental models;
- Problem Bank authoring;
- Solve Records and durable Evidence;
- human-readable review notes and reflections.

Do not use for:
- live scheduling logic;
- hidden mastery formulas;
- a second implementation runtime;
- manually asserting mastery without evidence.

### GitHub

Use for:
- the published deterministic learning contract;
- source code and solution metadata;
- curriculum snapshots consumed by runtime;
- tests, CI, versioning, PR review, releases;
- reproducible validation of curriculum rules.

Notion draft state does not become runtime truth until it passes compile/validate/review/CI and is published to Git.

### VS Code

Use as the **single default learner-facing operational surface**:
- Today;
- Learn;
- Practice;
- Review;
- Build / Run / Debug;
- Finish attempt;
- evidence capture;
- progress and memory maintenance;
- quality gate.

### ChatGPT

Use for:
- explanation;
- tutoring;
- hinting;
- debugging;
- error diagnosis;
- reflection;
- evidence proposals when the attempt context is available.

ChatGPT never silently invents attempt facts or directly awards mastery.

### Cloudflare / web surfaces

Retain only where the browser materially improves learning:
- interactive visualization;
- targeted lab;
- read-only dashboards;
- Notion writeback endpoint.

It must not become another parallel curriculum runtime.

## 3. Authority model

The system distinguishes **authoring authority**, **published runtime authority**, and **durable learning records**.

### Curriculum definitions

```text
Notion draft
  -> curriculum compiler
  -> validation
  -> Git diff / PR
  -> CI
  -> published curriculum snapshot
  -> VS Code runtime
```

The runtime reads the published Git snapshot, not live Notion.

### Attempt and evidence records

```text
VS Code attempt
  -> local durable outbox
  -> idempotent Notion writeback
  -> REC / Evidence
  -> derived mastery / memory state
```

Facts are captured once. Unknown information remains unknown.

### Generated state

The following are **derived**, not independent truth:
- Skill Status;
- RM / IM / RR / IR;
- memory stability;
- retrievability;
- next-review estimate;
- daily plan;
- dashboards.

Derived state must be reproducible from durable inputs plus a versioned algorithm.

## 4. Learning model

The current flat "tag everything equally" model is insufficient.

v2.3 separates three axes:

1. **Concept / Technique Skill**  
   Example: Prefix Sum, Binary Search, DFS, Greedy.

2. **Problem-solving competency**  
   Example: modeling, complexity reasoning, debugging, testcase design, correctness reasoning.

3. **Assessment capability**  
   Example: unfamiliar transfer, timed mixed solving, contest triage.

A problem may involve several concepts, but that does not mean one AC is equal evidence for all of them.

### Primary vs supporting skills

Every published practice placement should distinguish:
- primary Skill;
- supporting Skills.

Evidence must identify the Skill and Track actually observed.

## 5. Role and placement model

Worked Example / Guided Drill / Core Independent / Transfer Challenge / Mock are not intrinsic permanent properties of a problem.

They belong to a **placement/activity**.

A single problem can legitimately appear with different roles at different times, provided novelty/evidence interpretation remains honest.

## 6. Review and memory principles

The scheduler must not use a fixed sequence such as:

```text
1d -> 3d -> 7d -> 30d -> 60d -> 90d
```

and must not define graduation as "review N times".

The operational memory unit is:

```text
Skill x Track
```

The model may maintain:
- stability;
- retrievability;
- lapse count;
- evidence count;
- latest evidence quality.

These values are estimates and must be rebuildable from durable evidence plus the versioned scheduler.

### Evidence quality matters

A delayed, A0, independent, fresh transfer PASS is stronger retention evidence than:
- a same-day repeat;
- a heavily hinted AC;
- repeating the same memorized problem.

### No permanent graduation

A mature Skill can have a very long stability interval, but new evidence may return it to Review Due.

## 7. Workload governor

Daily review is capacity-limited.

Default policy starts around:
- review: 25-35% of APCS capacity;
- new learning / deliberate practice: 65-75%.

This is a starting policy, not a permanent constant.

Hard invariants:
- review candidates may be deferred;
- deferred review is not debt;
- backlog must not linearly accumulate;
- new-learning capacity must remain protected;
- problem-bank growth must not force daily review growth.

Mature maintenance should shift from permanent per-problem reviews to representative Skill retrieval and mixed practice.

## 8. Sync failure boundary

Authoritative mutation and generated sync are separate outcomes.

Correct behavior:

```text
authoritative mutation PASS
generated sync FAIL
=> mutation remains successful
=> show sync warning
=> retry sync independently
```

A generated-artifact failure must never cause the UI to report that already-committed learning facts were rolled back when they were not.

## 9. Notion migration policy

Existing Notion content is treated as input to audit, not unquestionable truth.

Every field must be classified as one of:
- KEEP;
- DERIVE;
- MOVE TO GIT;
- SYSTEM-MANAGED;
- DELETE;
- ARCHIVE.

No destructive Notion migration occurs until:
1. the field audit is complete;
2. the replacement runtime path is implemented;
3. readback proves no data loss;
4. migration is reversible.

## 10. Gate 0 acceptance

Gate 0 is complete only when:
- this architecture contract exists in Git;
- a machine-readable version exists;
- Notion core fields have an explicit migration classification;
- tests enforce the key authority invariants;
- no learner data has been mutated yet.

