# APCS-Practice v2.2 Workflow

## 1. 核心原則

v2.2 將資料分成四層：

1. **Problem Catalog**：`data/problems.csv`，保存題目 ID、名稱、來源、難度與 tags。
2. **Solution Catalog**：`data/solutions.csv`，連結 `.cpp` / `.py` 解法並保存 language 與 complexity。
3. **Learning state**：`data/progress.csv` 與 `data/reviews.csv`，保存 Finish / Review 與複習狀態。
4. **Notes**：`notes/<id>.md`，只在有價值時建立。

資料夾不再代表能力分類；能力分類由 Problem Catalog 的 metadata 推導。

日常操作以 VS Code 為主：`Ctrl+Shift+B` 編譯並執行目前 C++，`Ctrl+Alt+A` 開啟 APCS 控制中心。CLI 保留給除錯、自動化與進階操作。

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

日常使用 **APCS 控制中心**。確認 Judge 結果後，系統依序收集：

```text
Result
→ Recall（v2.2 相容自評）
→ Minutes
→ Assistance A0–A5
→ Independent
→ Novelty
→ Published Placement / Primary Skill
```

Assistance 沿用 APCS Learning System 的 learner labels：

- A0：完全獨立
- A1：只有診斷
- A2：概念提示
- A3：方向提示
- A4：骨架提示
- A5：完整參考

重要 Evidence facts 不使用隱性預設。

如果 `curriculum/published.v23.json` 能明確解析目前題目的 Placement，系統只為 **Primary Skill × Implementation** 建立 Evidence；Supporting Skills 不因為同一題 AC 就自動獲得 mastery evidence。

如果 Published Placement 缺失或 snapshot 尚未建立：

```text
Attempt 仍保存
Skill Evidence = 不建立
```

不得回退到舊 Tags 猜 Skill。

本機先寫入：

```text
.apcs/runtime/outbox/
```

remote Notion writeback 失敗不會要求重做題目。

Recall 0–3 暫時保留作 v2.2 相容欄位，但 **不再映射固定 1/3/7/30/60/90 天排程**。v2.3 的複習間隔由 Skill × Track Stability / Retrievability 與 Evidence quality 推導。

CLI `finish/review` 目前仍屬 v2.2 compatibility path；正式 learner-facing Evidence capture 以 Control Center 為準。

---

## 4. 複習

Review 同樣由 Control Center 記錄完整 attempt facts。

v2.3 不把每一個歷史 Problem 永久排入自己的複習序列；成熟 Skill 將逐步轉向 representative transfer / mixed practice。

目前舊 `data/progress.csv` / `data/reviews.csv` 與 legacy Today queue 暫時保留作相容層，直到 Skill × Track memory store 與 capacity-aware Today plan 完成切換。它們不再被視為 v2.3 的最終 scheduling authority。

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
今日複習
  ↓
完成到期／逾期題
  ↓
做新題
  ↓
AC → 完成題目
  ↓
必要時建立題目筆記
  ↓
檢查與提交
  ↓
Quality Gate PASS
  ↓
Commit / Push
```

一般日常操作不需要手動編輯 CSV，也不需要記住 CLI 指令。CLI 保留給 debugging、自動化與進階操作。

Dashboard、Problem Index 與 Review Queue 由 `tools/apcs.py sync` 與 GitHub Actions 維持。
