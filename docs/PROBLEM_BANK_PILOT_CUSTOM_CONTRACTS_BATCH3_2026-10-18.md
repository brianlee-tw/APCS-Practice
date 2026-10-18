# Problem Bank Pilot｜Batch 3：五題 Custom Lesson Contracts

**日期：** 2026-10-18  
**狀態：** `LESSON_CONTRACT_REVIEWED_TASK_INSTANCE_PENDING`  
**來源：** Notion 正式課程 / AI Coach Contract；Published Curriculum 已有的五筆 Custom PB UIDs  
**工程界線：** 本批只建立 rubric/anti-spoiler/source QA。**未取得 Hosted Workspace 的逐題完整題面**，未建立 Custom `tests.json`，不進 local Test Center，不產生 Evidence，不改 Notion/Published。

## 來源與課程證據

- [Notion L-PSV-02｜Complexity](https://app.notion.com/p/3c743be958cd8136b049f1ca91269687)：PB-160 Guided 12 min、PB-161 Core 15 min，需從 operation count/loop bound 推導 time、space、feasibility；PB-161 是 S30 Gate candidate。
- [L-PSV-02 AI Coach](https://app.notion.com/p/3c943be958cd810fa1effe30cbe5570a)：PB-160 是 Learning-only；PB-161 要紀錄 operation-count rationale、time、extra space、constraints、bottleneck；只有 Big-O 標籤不夠。
- [Notion L-PSV-03｜Code Reasoning](https://app.notion.com/p/3c743be958cd81a8a0bbdc932ae7dd13)：PB-164 明定 Reading Gate candidate、PB-165 明定 Implementation/Testing Gate candidate；兩者是不同 failure modes。
- [L-PSV-03 AI Coach](https://app.notion.com/p/3c943be958cd81379cc1cd578e272344)：PB-164 需要 trace/output prediction/completion rationale/second testcase；PB-165 需要 minimal counterexample、expected/actual first divergence、root cause、minimal patch、至少 3 個 regression tests。
- [Notion L-ORD-02｜Struct / Pair](https://app.notion.com/p/3c743be958cd81ad903ff74ea4899a61)：PB-169 Core Independent：score 降冪、penalty 升冪、完全 tie 保留原輸入順序；正式 Hosted Custom OJ 為 lesson 規範，但真實 code／comparator reasoning 仍是 Gate Evidence 必要部分。

上述資料證明 **正式教學契約**，而不是證明本批已讀取 Hosted runtime 原始 task payload。Notion 的舊 production receipt 不可拿來替代今天的真人學習者驗收。

## 五筆資料模型

| PB UID | 類型 | Track | 現行 Role | 正確驗證／Evidence | Gate |
| --- | --- | --- | --- | --- | --- |
| PB-160 | Complexity Budget | Reading | Guided Drill | repeated operation、iteration bounds、time/space/budget | Learning-only |
| PB-161 | Complexity Core | Reading | Core Independent | independent time/space rationale、constraint feasibility、bottleneck | S30 conditional candidate |
| PB-164 | Trace + Completion | Reading | Core Independent | **response-first** trace / prediction / minimal completion + second testcase | S39 Reading conditional candidate |
| PB-165 | Minimal Counterexample | Implementation | Core Independent | failing case、expected/actual first divergence、root cause、minimal patch、≥3 regression tests | S39 Debug/Testing conditional candidate |
| PB-169 | Multi-key record sort | Implementation | Core Independent | Hosted Custom OJ + actual record/comparator reasoning, time complexity | S08 conditional candidate |

這些都是**已有 Published 的五題**。來源分類不能取代尚待取得的原始任務實例。讀懂教程、看過答案、經過提示修正，都不能登記為新題 independent Gate evidence。

### 防劇透與解題權威

- `PB-160`：A1 只能問 repeated statement 與 loop bounds；A2 之後才進 iteration space。
- `PB-161`：A0 不展示 Big-O table，A1 僅問 iteration count / input dimension；A2+ 不算 independent。
- `PB-164`：A0 先完成正式 Reading 回答，不能預先公開 trace table / invariant / missing-line pattern；A1 僅問 state 語意。
- `PB-165`：A0 不洩漏 bug category / bug location / failing dimension；A1 僅診斷漏測哪個 dimension。
- `PB-169`：A0 不提供 comparator code、stable_sort 選擇、original-index strategy、完整 tie-break 解法；不能僅靠 Custom Judge PASS 宣告 S08 Gate mastery。

### 新增工程資產

- `data/problem_pilot/custom_contracts_batch3.v1.json`：已確認的正式課程契約與明確未取得項目。
- `tools/pilot_custom_contracts.py`：唯讀檢查 5 個 PB UID、Published Placement、Notion URL、Role、Track、Gate/rubric、A0 disclosure firewall、所有非發布狀態。
- `tests/test_pilot_custom_contracts.py`：拒絕將 Reading Gate 改成 OJ exact checker、刪除必需 regression artifacts、在 A0 洩露方法、偽造 learner Evidence、擅自標示資料已驗證。
- `tools/pilot_release_preflight.py` 與 `tests/test_pilot_release_preflight.py`：把此批納入既有 **engineering PASS / release BLOCKED_MANUAL** 規則，預期本批 `5 reviewed lesson contracts / 0 verified task packets / 4 conditional Gate candidates`。

## Pilot 累計狀態（本批完成後）

- 18 Seed 題目。
- 4 ZeroJudge 題已完成來源與官方樣例，17 組加強測資差分驗證，仍未真人實機驗收。
- 5 CSES / Codeforces 題來源已核對，維持 staged，不進 Test Center；CF 977C 須特殊 checker。
- 本批 5 Custom 題已核對 Notion Lesson Contract，但逐題 canonical task instance 尚未取得、不得視為教學素材全量核對。
- **剩餘 4 題**：PB-120 APCS q836、PB-97 Codeforces 71A、PB-10 ZeroJudge q182、PB-32 ZeroJudge a233。官方內容取不到時，標記 SOURCE_PENDING，絕不推測 samples 或題意。
- Learner readiness `NOT_ASSESSED`；C8 `OPEN`；PR #89 `Draft` 且未合併。

## 下一個 Content Gate

優先取得剩餘四題的完整官方題面與 sample。若非 ZeroJudge／Custom 類型可取得可靠來源，也先存 staging，不在同一階段匆忙擴張 L0 importer 或完整 Judge adapter。若要將 Custom 五題正式接到 VS Code Test Center，須先釐清 Reading response-first 與 Hosted Custom OJ 的權威，不得拿單一 exact-output runner 假裝已完成這些功能。
