# APCS 題庫 Pilot｜品質審核與 Workbench 整合紀錄

**日期：** 2026-10-18  
**範圍：** PR #89 Draft，4 題既有 Published ZeroJudge 題目及其 Test Center 資產  
**決策：** ENGINEERING_CHECK_PASS / HUMAN_LEARNER_ACCEPTANCE_PENDING / L1_ADOPTION_PENDING  
**權威：** 題面與測資範例採 ZeroJudge，正式 Skill/Role/Placement 仍以既有 Published/Notion 為準。

## 1. 來源與內容品質

| PB UID | 官方題目 | Published Primary / D / Role | 官方範例 | AI 加強測資 | QA 判斷 |
| --- | --- | --- | ---: | ---: | --- |
| PB-182 | [d067 閏年](https://zerojudge.tw/ShowProblem?problemid=d067) | S02_Conditionals / D2 / Core Independent | 4 | 6 | Source/model consistent, AI 未正式採納 |
| PB-183 | [d097 Jolly Jumpers](https://zerojudge.tw/ShowProblem?problemid=d097) | S05_Array / D2 / Core Independent | 1 | 4 | Source/model consistent, 多行 EOF 與差值去重有涵蓋 |
| PB-27 | [d732 二分搜尋法](https://zerojudge.tw/ShowProblem?problemid=d732) | S10_Binary_Search / D2 / Guided Drill | 1 | 3 | Source/model consistent, **alternative-method mastery risk** |
| PB-9 | [j606 造字程式](https://zerojudge.tw/ShowProblem?problemid=j606) | S34_Matrix_2D / D3 / Core Independent | 2 | 4 | **AI NEEDS_QA**，不得自動授予分類確認 |

- 四題官方公開範例合計 **8 組**，另有 **17 組**以 ChatGPT 設計並經兩種獨立參考演算法差分比對的加強測資。
- 880 組固定種子隨機有效輸入（每題 220 組）已納入回歸測試；另有在 CI 執行時產生的 d732 100000×100000、d097 n=2999、j606 K=Q=R=20 邊界規模測試（不額外提交巨型靜態測資）。
- `DIFFERENTIAL_VERIFIED` 僅指兩套參考方法在已測範圍內一致；不代表 OJ AC、隱藏測資正確率或 learner mastery。
- 本批不建立或覆寫完整題面、L2 教材、Attempt、Evidence、Notion 正式內容。

## 2. Primary Skill 專項判斷

### PB-9 / j606 — 保留既有 Primary，AI 仍 NEEDS_QA

ZeroJudge 官方標籤同時有 **二維陣列**與**字串**。題意包含：每次依 `P_i` 把舊位置 `i` 放到新位置 `P_i`，並輸出每次修改結果的前 `R` 個位置，形成 `R×Q` 的行列轉置輸出。因此現有 `S34_Matrix_2D` 作為 Lesson 的主要檢驗面向有依據，`S07_String`、`S23_Simulation` 作 supporting skills 也合理。

**不變更 Published Placement。** 此處只是 ChatGPT 的專業複核理由；既有候選的 confidence 0.77 與歧義註記仍保留 `NEEDS_QA`，等待教學目標層面的 curator decision。不要透過調高 AI confidence 來清除 QA。

### PB-27 / d732 — AC 不一定能驗證 Binary Search

來源數列已嚴格遞增、查詢很多，Binary Search 是自然且有效的教學目標；但也可透過 associative container / index map 取得正確輸出。即使 learner 獲得 OJ AC，也不保證使用了目標 `S10_Binary_Search`。Published Placement 目前 `method_confirmation_required=false`，所以應以後續真實 Evidence/方法檢查作為保護，不直接將 AC 解讀成此 Skill mastery。

**此 PR 不修改 Published method-confirmation policy。** 待確認此題是否作為 Gate-grade Evidence，才按正式 SSOT 修正，不在 Pilot 中私下替換權威欄位。

## 3. Workbench 關鍵整合缺口與修復

原程式中：

- Control Center 產生 `zj-d732__PL-PB-27-L-BIN-01.cpp` 類型檔名；
- Published `problem_id` 是 `zj-d732`，testcase 目錄的 judge-local external ID 卻是 `d732`；
- `PLACEMENT_RE` 沒包含連字號，導致真實 Published Placement suffix 解析失敗；
- `vscode_task._test_bundle` 直接以 namespaced ID 查找，會讓 Test Center 找不到 Pilot 新增的測資。

本輪已在 `tools/workbench_context.py` 與 `tools/apcs_control.py` 最小修正 Placement parser，並在 `tools/vscode_task.py` 加入 **source URL 驗證後的 ZeroJudge identity 對應**。不可因字首看似 `zj-` 就盲目剝除；必須先核對 canonical URL、來源、external ID。錯誤 URL、另一題或缺失 authoritative URL 均 fail closed。

`tests/test_pilot_integration_acceptance.py` 使用正式 Published 4 筆 Placement 建立**不寫入本機的虛擬 scratch path**，從 `problem_context()` 解析、交給 `_test_bundle()` 讀取實際資料，並檢查：

1. Placement UID、PB UID、ZeroJudge external ID 與 canonical URL 一致；
2. Official 8 組與 Differential Verified 17 組可依題成功載入；
3. Practice Fast 僅官方範例、Practice Full 包含 verified cases；
4. Exam / Transfer 作答前仍僅可見官方範例，作答後才可用 Full repair cases；
5. 已驗證的負向案例：錯誤 URL、跨題 URL、錯誤來源、缺少 namespaced ID 的權威 URL 均不誤載測資。

## 4. 驗收界線

**已驗證的 engineering evidence：** 自動回歸、資料資產一致性、兩組 oracle、固定種子 fuzz、邊界規模、真實函式層級 Test Center 整合、GitHub CI。

**尚未完成：** 使用者本機 VS Code 鍵盤操作、實際 `Ctrl+Shift+B` 端到端 UI、真實 learner 寫程式 → OJ → Evidence 完整路徑、j606 curator final decision、d732 method_confirmation policy decision、其他 14 題的 source QA。

不可將這份工程紀錄解讀為 `C8` 完成或 `LEARNER_READINESS` 評為 PASS。PR #89 保持 Draft、不 merge。


## 5. Follow-up policy reconciliation (2026-10-18 evening)

Following the earlier report's open questions, re-read the **canonical Notion Lessons** (read-only, no Notion writes) and resolved the **existing Published policy choice**, while retaining AI candidate QA.

| PB UID | Lesson authority | Source-backed interpretation | Decision |
| --- | --- | --- | --- |
| PB-9 / j606 | [Notion L-DAT-03](https://app.notion.com/p/3c743be958cd811189fcd92a60c2a758), [AI Coach](https://app.notion.com/p/3c943be958cd813fad27c905cde26caf) | Lesson deliberately tests **S34_Matrix_2D** via source→destination mapping, multi-step state and R×Q output; String/Simulation remain supporting. Core Independent, A1 only diagnostic; A2+ cannot claim independent evidence. | **Keep Published unchanged.** ChatGPT classification **NEEDS_QA** and formal human L1 adoption still pending. |
| PB-27 / d732 | [Notion L-BIN-01](https://app.notion.com/p/3c743be958cd81a9af82fdcf7ce5f004) | Explicit **Guided Drill / Learning-only**, not S10 gate; actual independent core gate candidate in lesson is **PB-24**. Published evidence cap 2, method_confirmation_required=false already reflect learning-only. | **Keep Published unchanged.** No extra method-confirmation rule needed for this learning-only exercise; OJ AC alone never upgrades S10 mastery. |

These decisions resolve earlier *policy doubts* without pretending that an AI classification proposal has been approved or that any learner mastered these methods.

A machine-readable `data/problem_pilot/policy_review.v1.json` records the Notion source URLs, Published placement invariants, decisions and **PENDING** reviewer/learner gates.

## 6. Automated release preflight

Added read-only `tools/pilot_release_preflight.py`, covered by `tests/test_pilot_release_preflight.py`.

It verifies:
- Git-blob hash pins for `curriculum/published.v23.json` and `docs/CURRENT_AUTHORITY.json` from known main; drift fails instead of silently accepting a new curriculum;
- 18-item Pilot seed and four source receipts, four ChatGPT proposals/QA statuses, and the policy's exact two Published Placements;
- eight `OFFICIAL` cases, 17 `AI_GENERATED / DIFFERENTIAL_VERIFIED` cases, Full-only exposure and strict Exam pre-attempt official-only restriction;
- no implicit Notion/Published mutations, AI L1 approval, learner Evidence, C8 closure, readiness promotion, or merge permission.

The output is intentionally:
```text
PILOT PREFLIGHT PASS / RELEASE BLOCKED_MANUAL | 8 official / 17 edges
```

**PASS** is only the reproducible engineering preflight, **BLOCKED_MANUAL** is the actual release state. The checker does not query current GitHub CI itself, which is verified separately.

Operator check on the PR branch:
```bash
python3 tools/pilot_release_preflight.py
python3 -m unittest tests.test_pilot_release_preflight -v
```

CI `APCS Validate #294` passed at `12d56286cf325d542826f0c9601370f658d36284`. This earlier report's open issues for j606/d732 are now **policy-reconciled**; the remaining gates are genuine learner VS Code acceptance, human authorization to merge, and separate human approval before any L1 candidate adoption.

**Still not executed:** a real learner Test Center session, external OJ submission, Evidence writeback, or any Notion/Published change. C8 remains OPEN; LEARNER_READINESS remains NOT_ASSESSED.
