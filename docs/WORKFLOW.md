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

目前 v2.2 migration 階段，新題目需要同時：

1. 建立純 `.cpp` / `.py` solution file。
2. 在 `data/problems.csv` 建立 problem metadata。
3. 在 `data/solutions.csv` 建立 solution path / language / complexity。
4. 執行 `python tools/apcs.py validate` 驗證 Catalog consistency。

solution source 不再需要 `APCS Title`、`APCS Tag`、`APCS Complexity`、`APCS Note`、`APCS Date` 等 metadata headers。Control Center 的新增題目 workflow 將在 v2.2 後續 Gate 接管這些操作。

---

## 3. 做完一題

確認 Online Judge 為 AC 後：

```powershell
python tools/apcs.py finish b130 2
```

其中 Recall：

| 分數 | 定義 | 下一次複習 |
|---:|---|---:|
| 0 | 幾乎不會 / 看答案才懂 | 1 天 |
| 1 | 需要提示 | 3 天 |
| 2 | 可獨立完成但偏慢 | 7 天 |
| 3 | 流暢獨立完成 | 30 天 |

只有正式 Review 的 `AC + Recall 3` 才累積 streak，而且必須發生在不同日期。同一天多次 Review 只採最後一筆參與 streak 計算。第 1 次為 30 天、第 2 次為 60 天、第 3 次以上為 90 天；較低 Recall 或非 AC 會中斷 streak。

可額外記錄時間：

```powershell
python tools/apcs.py finish b130 2 --minutes 18
```

---

## 4. 複習

日常使用 APCS 控制中心的「今日複習」查看並開啟到期題目。

重解後，由控制中心依序記錄：

```text
Result → Recall → Minutes
```

Result 支援 `AC`、`WA`、`TLE`、`RE`、`MLE`、`CE`。Minutes 可略過；非 AC 不允許 Recall 3。

CLI 等價操作：

```bash
python tools/apcs.py today
python tools/apcs.py review b130 3 --minutes 7
python tools/apcs.py review b130 1 --result WA --minutes 11
```

Review 失敗不會移除既有首次 AC。`solved_on` 表示首次完成日期；`last_review_on`、`last_result` 與 `recall` 則描述最近一次複習狀態。

只有正式 Review 的 `AC + Recall 3` 會累積 streak，而且必須來自不同日期；同一天多次 Review 只採最後一筆。第 1、2、3 次連續成功分別對應 30、60、90 天。較低 Recall 或非 AC 會中斷 streak。

這些紀錄會寫入：

- `data/progress.csv`：目前學習狀態快照。
- `data/reviews.csv`：Finish / Review 的事件歷史，包括 Result、Recall 與 Minutes。

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

```powershell
python tools/apcs.py validate
```

Catalog metadata 不完整時會以 warning 呈現，例如缺少 title、tags 或 complexity。Catalog 結構錯誤、solution 指向不存在題目、solution file 不存在，以及損壞的 learning data 都屬於 error，會使驗證失敗。

若要把 warning 也視為 failure：

```powershell
python tools/apcs.py validate --strict
```

---

## 8. Git / GitHub 自動化

### Pull Request / push validation

GitHub Actions 會：

1. 執行 metadata / learning-data validator。
2. 只對本次新增或修改的 `.cpp` / `.py` solution 做 syntax check。
3. 不會因歷史題目中仍存在的 v1 warning 阻擋所有開發。

### main dashboard sync

main 收到新 solution / progress / review / tooling 變更後：

1. 執行 `python tools/apcs.py sync`
2. 只 stage `README.md`、`docs/PROBLEM_INDEX.md`、`docs/REVIEW_QUEUE.md`
3. 有差異才 commit
4. 不再 `git add .`
5. 不再自動 `pull --rebase`

---

## 9. 舊四資料夾

v1 的四個資料夾保留，以避免一次性搬移 58 題造成大量無學習價值的 Git churn 與連結斷裂。

v2 的能力分類改為：

- Graph
- DP / Recursion
- Prefix / Greedy
- Search / Sort
- Data Structures
- Math
- String
- Arrays / Simulation
- Fundamentals / Simulation

因此同一題可以靠多個 tags 表達真實能力，而不是被迫放進唯一一個資料夾。

---

## 10. 建議每日操作

```text
開始 APCS
  ↓
python tools/apcs.py today
  ↓
先重解 1~3 題到期題
  ↓
做新題
  ↓
AC → python tools/apcs.py finish <id> <score>
  ↓
必要時 python tools/apcs.py note <id>
  ↓
git commit / push
```

Dashboard 和索引由工具與 GitHub Actions維持。
