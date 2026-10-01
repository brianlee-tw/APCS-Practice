# APCS-Practice v2.3 Workflow

## 1. 核心原則

v2.3 把「工程資料」與「學習 runtime」分開：

1. **Problem / Solution Catalog**：repo 內工程 metadata、solution path、language、complexity。
2. **Published Curriculum**：由 Notion authoring 經 compiler / validation / Git review 後產生的 runtime snapshot。
3. **Compatibility learning history**：data/progress.csv 與 data/reviews.csv，保留 v2.2 歷史與過渡狀態。
4. **Durable local Evidence outbox**：.apcs/runtime/outbox/，一次 Attempt 只記一次，remote writeback 可重試。
5. **Adaptive Skill memory**：.apcs/runtime/skill_memory.json，屬於可重建 derived cache，不是新的 SSOT。
6. **Notes**：notes/<id>.md，只在有長期價值時建立。

日常 learner surface 是 VS Code Control Center。Notion 負責 curriculum authoring、long-form teaching、REC / Evidence durable record；Git 負責 published contract、code、tests、CI；ChatGPT 負責 coach / explanation / debugging，而不是 mastery authority。

固定 1/3/7/30/60/90 天與「複習 N 次畢業」已退出 learner-facing runtime。Review 使用 Skill × Track Stability / Retrievability，加上每日 capacity governor；deferred review 不視為欠作業。

日常操作以 VS Code 為主：Ctrl+Shift+B 編譯並執行目前 C++，Ctrl+Alt+A 開啟 APCS 控制中心。Finish / Review 不應透過舊 CLI 繞過 Evidence capture。

---

## 2. 新題目

日常操作由 **APCS 控制中心 → 題目資料 → 新增題目** 完成。

建立一題時，系統會：

1. 建立純 `.cpp` / `.py` solution file。
2. 寫入 `data/problems.csv` 的 problem metadata。
3. 寫入 `data/solutions.csv` 的 solution path、language 與 complexity。
4. 使用 canonical Tag selector 選擇一個以上的能力 Tag。
5. 以 rollback-safe Catalog mutation 避免兩份 CSV 只成功一半。

solution source 不承載 `APCS Title`、`APCS Tag`、`APCS Complexity`、`APCS Note` 或 `APCS Date` 等 metadata header。

`data/problems.csv` 與 `data/solutions.csv` 是 metadata 的唯一 engineering truth。

---

## 3. 做完一題

確認 Online Judge 結果後，使用：

```text
Ctrl+Alt+A
→ 完成題目
```

Control Center 會記錄：

- Result / Recall / Minutes；
- A0–A5 Assistance；
- Independent；
- Novelty；
- Timed；
- Published Curriculum Placement；
- explicit Primary Skill × Implementation Evidence。

Recall 只描述本次主觀回憶品質：

| 分數 | 定義 |
|---:|---|
| 0 | 幾乎無法自行重建／需要看答案 |
| 1 | 有部分記憶，但需要提示 |
| 2 | 可獨立完成，但速度或穩定度不足 |
| 3 | 流暢、獨立完成；不代表永久 Mastered |

若 Published Placement 尚不存在，Attempt 仍會保存，但不會從 repo Tags 猜 Skill Evidence。

A2–A5 強制 Independent=false；A0/A1 仍由使用者明確確認，避免把 Assistance 誤當成能力證據。

完成紀錄會先進 durable local outbox，再更新可重建 adaptive memory。Notion writeback 失敗不代表要重做題目。

---

## 4. 今日學習與 Adaptive Review

使用：

```text
Ctrl+Alt+A
→ 今日學習
```

Today 會先從 durable Evidence reconciliation 出 Skill × Track memory，再建立 capacity-aware review plan。

預設 60 分鐘 session：

- Review target：18 分鐘；
- Review hard max：依 policy 限制；
- New learning：保留至少 42 分鐘；
- 超出容量的 due Skills：deferred，不算 backlog debt。

Review priority 使用透明排序：recent failure → curriculum importance → 較低 Retrievability → 較久 overdue → 能塞入剩餘時間的較短任務。

Implementation review 會優先選 Published Placement 的 fresh / unattempted representative problem，並建立：

```text
.apcs/runtime/review/<date>/<problem_id>__<placement_uid>.cpp
```

這是空白 retrieval scratch，不會打開歷史 solution。完成 Judge 後回 Control Center 選「複習題目」，Placement UID 會沿用到 Evidence。

Reading review 不自動開歷史 solution，也不在正式回答前執行程式驗證。

v2.2 的 problem-level due state 仍暫時保留作相容資料，但已不是 learner-facing Today scheduler。

---

## 5. 筆記

一般題不需要額外筆記；solution、Catalog metadata 與 review history 通常已足夠。

只有值得整理的題目才建立 repo 內短筆記：

```powershell
python tools/apcs.py note b130
```

會建立：

```text
notes/b130.md
```

筆記與題目 metadata 分離，不需要修改 solution source。

---

## 6. 自動產生索引

手動同步：

```powershell
python tools/apcs.py sync
```

會更新：

- `README.md`
- `docs/PROBLEM_INDEX.md`
- `docs/REVIEW_QUEUE.md`

舊指令仍可使用：

```powershell
python tools/sync_all.py
```

---

## 7. 驗證

完整本機 quality gate：

```bash
python3 tools/quality_gate.py
```

它會依序檢查：

1. 完整 regression tests。
2. `git diff --check` 與 staged whitespace。
3. Catalog / learning-data validation。
4. known-warning budget。

目前少數歷史題目仍有明確列出的 metadata 缺口；這些 warning 被記錄在 `.github/apcs-known-warnings.txt`。既有 warning 可以減少，但新增或重複增加的 warning 會使 quality gate 失敗。

只執行 validator：

```bash
python3 tools/apcs.py validate
```

Catalog 結構錯誤、solution path 不存在、learning snapshot/event 不一致等屬於 error，會直接失敗。

metadata 不完整則維持 unknown，不應為了消除 warning 猜測 Title、Tag、Complexity 或其他資料。

---

## 8. Git / GitHub 自動化

### Control Center commit

「檢查與提交 → 建立 Commit」會先執行完整 regression 與 warning-budget quality gate。Gate 未通過時不建立 commit。

### GitHub Actions

Pull Request / main push 會：

1. 執行完整 regression tests。
2. 驗證 Catalog 與 learning data。
3. enforce known-warning budget。
4. syntax-check 本次新增或修改的 solution source。

### main dashboard sync

main 收到 solution、data、notes 或 tooling 更新後：

1. 執行 regression 與 warning-budget gate。
2. 執行 `python3 tools/apcs.py sync`。
3. 只 stage `README.md`、`docs/PROBLEM_INDEX.md`、`docs/REVIEW_QUEUE.md`。
4. 有 generated diff 才建立 sync commit。

---

## 9. 舊四資料夾與能力分類

`01_Basic_Syntax_Optimization`、`02_Data_Structures`、`03_Algorithmic_Paradigms`、`04_Graph_Theory_and_Advanced_Topics` 是歷史檔案位置，不代表目前能力分類。

v2.2 使用 canonical multi-tag taxonomy：

- **基礎**：Basic Syntax、I/O、Conditionals、Loops、Simulation
- **資料結構**：Array、Vector、String、Struct、Stack、Queue、Set、Map
- **演算法**：Sorting、Searching、Binary Search、Prefix Sum、Two Pointers、Greedy
- **數學**：Math、Number Theory、Prime、GCD / LCM、Geometry、Combinatorics
- **圖論**：Graph、BFS、DFS、Shortest Path
- **進階**：Dynamic Programming、Recursion、Backtracking

一題可同時計入多個 canonical Tags。Dashboard 的弱項訊號只使用可觀察資料：`Recall 0–1` 或到期題目，不建立黑箱能力分數。

無法安全自動轉換的歷史 Tag 會標示為 `Legacy`，保留原值等待人工確認。

---

## 10. 建議每日操作

```text
Ctrl+Alt+A
  ↓
今日學習
  ↓
Adaptive review（只有真的需要的 Skill）
  +
保留新學習容量
  ↓
依 Published Curriculum 學下一個 Ready Skill / Lesson
  ↓
Practice / Judge
  ↓
完成題目或複習題目
  ↓
Attempt → Evidence outbox → adaptive memory
  ↓
必要時建立題目筆記
  ↓
檢查與提交
  ↓
Quality Gate PASS
  ↓
Commit / Push
```

一般日常操作不需要手動編輯 CSV，也不應手動維護 next review。CLI 只保留 engineering / validation / sync 類操作；learner-facing Finish / Review / Today 以 Control Center 為準。

GitHub 上的 generated Dashboard / Review Queue 目前仍包含 v2.2 compatibility 資訊，不代表本機 v2.3 adaptive Today 的個人排程。

