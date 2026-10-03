# APCS-Practice

APCS C++ 學習、實作練習、複習排程與能力證據追蹤系統。

v2.3 的可靠學習基礎設施已完成並投入正式使用；v2.4 現在進入「低摩擦認知式學習系統」開發階段。日常仍以 VS Code 控制中心為主，不要求學習者管理底層資料。

<!-- APCS_CURRENT_AUTHORITY_START -->
## 目前正式狀態（自動產生）

> 本區塊由 `docs/CURRENT_AUTHORITY.json` 產生；不要手動修改。

- 穩定學習執行環境：**v2.3**，狀態 `PRODUCTION_CLOSED`。
- 下一版本：**v2.4**，目前階段 **C3｜題目庫與防劇透**。
- 正式課程：**52 Lessons / 14 Units / 39 Skills**；未有真實 Evidence 前不擴張主線。
- Production Worker：**#58 @100%** `0eafa60d-6d4d-4edb-b1eb-ac6a9a3625b6`；system-audit = **PASS_CLEAN**；Preview / Version URLs = **DISABLED**。
- 日常主要介面：**VS Code Control Center**。
- 學習準備度：`LEARNER_READINESS = NOT_ASSESSED`。
- v2.4 正式契約：[`docs/V24_PRODUCT_ARCHITECTURE_CONTRACT.md`](./docs/V24_PRODUCT_ARCHITECTURE_CONTRACT.md)。
<!-- APCS_CURRENT_AUTHORITY_END -->

這個倉庫仍保留 v2.2 的題目／解答資料底座作為相容層；它不是 v2.3/v2.4 的能力判定或今日學習權威。

## 目標

- APCS 觀念題與實作題持續提升。
- 不以「刷了幾題」取代真正的掌握程度。
- 將 **AC、重解結果、複習間隔、弱項** 變成可追蹤資料。
- 題目筆記只在有價值時建立於 `notes/<id>.md`，不依賴外部筆記連結。

## 最短工作流程

日常使用以 VS Code 為主，不需要記大量指令或快捷鍵。

### 主要入口

```text
Ctrl+Shift+B
→ 編譯並執行目前 C++ 題目

Ctrl+Alt+A
→ 開啟 APCS 控制中心
```

APCS 控制中心提供：

- **今日學習**：依 Skill × Track retention 與今日容量安排 adaptive review，同時保留新學習時間；Published Placement 可啟動 Reading 或 Implementation activity。
- **學習狀態**：查看 durable Evidence、Reading / Implementation 分布、Remote ACK / Pending、Skill × Track retention 與 capacity；不宣告 readiness。
- **完成題目**：Implementation 記錄 Judge result / Recall；Reading 先完成 formal response，再記錄 PASS / PARTIAL / FAIL Evidence。
- **複習題目**：Implementation 使用空白 retrieval scratch；Reading 使用 response-first scratch，兩者都回到同一 Evidence / adaptive-memory path。
- **題目資料**：管理 Problem metadata，並列出、開啟或新增同一題的多份 solution；Complexity 綁定實際 solution path。
- **題目筆記**：建立或開啟 `notes/<id>.md`。
- **檢查與提交**：檢視 Git 變更、stage、commit，以及確認後 push。

Recall 自評目前保留作為可觀察的主觀回憶品質，不再代表固定複習間隔：

| Recall | 定義 |
| ---: | --- |
| 0 | 幾乎無法自行重建／需要看答案 |
| 1 | 有部分記憶，但需要提示 |
| 2 | 可獨立完成，但速度或穩定度不足 |
| 3 | 流暢、獨立完成；不代表永久 Mastered |

v2.3 的複習方向改為 `Skill × Track` adaptive memory：間隔由實際 elapsed time、Assistance、Independent、Novelty、Outcome 與既有 Stability / Retrievability 推導，不使用固定 1/3/7/30/60/90 天，也不以「複習 N 次」畢業。

Control Center 的 Finish / Review 會另外收集 A0–A5 Assistance、Independent、Novelty、Timed 與 Published Curriculum Placement；本機先寫入 `.apcs/runtime/outbox/`。若 Published Placement 尚未建立，Attempt 仍保存，但不會猜測 Skill Evidence。

Evidence 會重建 `.apcs/runtime/skill_memory.json` 的 derived Skill × Track memory cache。Today 預設以 60 分鐘容量安排最多約 30% review，deferred Skills 不算欠題；Implementation review 會建立空白 retrieval scratch，而不是打開歷史 solution。

分鐘數屬於每次 Attempt 的事件資料，可略過；「有記錄耗時」不等於 Timed。

### CLI

控制中心是日常入口；CLI 保留給除錯、自動化與進階操作，例如：

```bash
python tools/apcs.py note b130
python tools/apcs.py validate
python tools/apcs.py sync
```

v2.3 的 Finish / Review / Today 不應繞過 Control Center；舊式 direct task path 已停用或保留為相容層，避免漏掉 Assistance、Placement、Evidence 與 adaptive memory。

v2.2 以 `data/problems.csv` 與 `data/solutions.csv` 作為靜態 metadata 的唯一正式來源；solution code 不再承載 `APCS` metadata header，也不再提供 source-header fallback。

### v2.2 核心保證

- Problem / Solution Catalog 是 metadata 唯一正式來源；solution source 保持純程式碼。
- `progress.csv` 與 `reviews.csv` 採 rollback-safe paired update，並驗證 snapshot / event consistency。
- 能力分析使用 canonical multi-tag taxonomy；一題可以同時計入多個能力 Tag。
- 弱項只根據 Recall 0–1 或已到期題目，不建立黑箱分數。
- known-warning budget 防止新的 metadata 缺口無聲增加。
- Control Center 建立 commit 前會執行完整 regression 與 quality gate。

<!-- APCS_DASHBOARD_START -->
## v2.2 Compatibility Dashboard

> 相容觀測面：不代表 v2.3 Skill × Track mastery、Today 排程或 readiness。

| 指標 | 數量 |
| :--- | ---: |
| 索引題目 | **58** |
| 明確 AC | **0** |
| v2.2 Mastered | **0** |
| v2.2 problem due | **0** |

### v2.2 Tag 統計（compatibility）

> 一題可同時計入多個 Tag，因此 Tag 題數加總可能大於索引題目總數。

| 類別 | Tag | 題數 | AC | v2.2 Mastered | Recall 0–1 | v2.2 due |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| 基礎 | Basic Syntax | 7 | 0 | 0 | 0 | 0 |
| 基礎 | I/O | 25 | 0 | 0 | 0 | 0 |
| 基礎 | Conditionals | 20 | 0 | 0 | 0 | 0 |
| 基礎 | Loops | 23 | 0 | 0 | 0 | 0 |
| 資料結構 | Array | 10 | 0 | 0 | 0 | 0 |
| 資料結構 | Vector | 7 | 0 | 0 | 0 | 0 |
| 資料結構 | String | 6 | 0 | 0 | 0 | 0 |
| 資料結構 | Struct | 1 | 0 | 0 | 0 | 0 |
| 演算法 | Sorting | 1 | 0 | 0 | 0 | 0 |
| 演算法 | Greedy | 1 | 0 | 0 | 0 | 0 |

### v2.2 觀測訊號

> 只使用可觀察資料：Recall 0–1 或已到期題目；不使用黑箱分數。

| Tag | 已 AC | Recall 0–1 | v2.2 due | v2.2 Mastered |
| :--- | ---: | ---: | ---: | ---: |
| — | — | — | — | 目前沒有明確弱項訊號 |

### Legacy Tag 待整理

> 下列標籤未被 taxonomy 自動推測或轉換；保留原值，待後續人工確認。

| Legacy Tag | 題數 |
| :--- | ---: |
| Math Theory | 19 |

### v2.2 Problem-level Due Queue

| ID | 題目 | Tags | Recall | 到期日 |
| :--- | :--- | :--- | ---: | :---: |
| — | 目前沒有到期題目 | — | — | — |

完整題庫見 [Problem Index](./docs/PROBLEM_INDEX.md)，相容佇列見 [Compatibility Review Queue](./docs/REVIEW_QUEUE.md)。
<!-- APCS_DASHBOARD_END -->

## 資料來源與可信度

- `data/problems.csv`：題目 ID、名稱、來源、難度與 tags。
- `data/solutions.csv`：solution 路徑、語言與 complexity。
- `data/progress.csv`：目前學習狀態（首次完成、最近 Review、Result、Recall）。
- `data/reviews.csv`：Finish / Review 的 append-only 事件歷史。
- `notes/<id>.md`：可選的 repo 內短筆記。

## 自動化

- Control Center 建立 commit 前：Python learning-runtime regression + diagnostic-site Node regression + whitespace check + Catalog / learning validation + warning-budget gate。
- Pull Request / main push：Python regression、diagnostic-site Node regression、warning-budget validation，以及本次修改 solution 的 syntax check。
- main 更新後：安全重新產生 README、Problem Index、Review Queue，只 stage generated artifacts。

## Standalone diagnostic site

`site/` 是獨立的匿名能力診斷 surface，**不是 v2.3 Learning Runtime**。它的 `site/data/skill-model.v1.json` 只服務 diagnostic UI，明確設定 `scope = diagnostic-only` 與 `readinessAuthority = false`；不得拿來取代 Skill Map v3、REC/EV、Skill × Track memory 或 RR/IR readiness。

完整 authority boundary 見 [site/README.md](./site/README.md)。

## Historical folders

`01_Basic_Syntax_Optimization`、`02_Data_Structures`、`03_Algorithmic_Paradigms`、`04_Graph_Theory_and_Advanced_Topics` 是 v1 歷史資料夾。v2 不再用它們當作能力分類或固定「50 題」進度 KPI。

## License

MIT License。
