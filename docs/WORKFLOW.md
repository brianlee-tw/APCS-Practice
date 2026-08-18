# APCS-Practice v2 Workflow

## 1. 核心原則

v2 將資料分成三層：

1. **Solution**：`.cpp` / `.py`，保存真正的解法。
2. **Learning state**：`data/progress.csv` 與 `data/reviews.csv`，保存 AC 與複習結果。
3. **Notes**：`notes/<id>.md` 或既有 Notion，只在有價值時建立。

資料夾不再代表能力分類；能力分類由 tags 與 metadata 推導。

---

## 2. 新題目

新題目放在 `solutions/`。建議檔名：

```text
b130_Random_Number.cpp
```

建議的最小檔頭：

```cpp
// APCS Title: b130. 明明的隨機數
// APCS Complexity: O(N log N)
// APCS Tag: Sorting, Set
// APCS Difficulty: 1
// APCS Source: https://...
```

Python 使用 `#`：

```python
# APCS Title: a010. 質因數分解
# APCS Complexity: O(sqrt(N))
# APCS Tag: Math, Prime
# APCS Difficulty: 2
```

`APCS Source` 可省略。新題目不需要再手動維護 `APCS Date`、`APCS Status`。

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

連續兩次 Recall=3 後，間隔拉長到 60 天；連續三次以上為 90 天。

可額外記錄時間：

```powershell
python tools/apcs.py finish b130 2 --minutes 18
```

---

## 4. 複習

看今天到期的題目：

```powershell
python tools/apcs.py today
```

重解後：

```powershell
python tools/apcs.py review b130 3 --minutes 7
```

若重解結果不是 AC：

```powershell
python tools/apcs.py review b130 1 --result WA
```

這些紀錄會寫入：

- `data/progress.csv`：最新狀態
- `data/reviews.csv`：歷史紀錄

然後自動重新產生 dashboard。

---

## 5. 筆記：Notion 不再是必填

### 一般題

不做額外筆記。程式碼、tags、複雜度和 review history 就足夠。

### 值得整理的題

建立 repo 內短筆記：

```powershell
python tools/apcs.py note b130
```

會建立：

```text
notes/b130.md
```

同步器會自動找到它，不必再修改程式碼 metadata。

### 舊 Notion

既有：

```text
APCS Note: https://...
```

會保留並繼續出現在索引中。

建議只把 Notion 留給：

- 需要圖解的演算法
- 有多種解法比較
- 常犯錯、值得寫長反思
- APCS 經典題型整理

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

目前 v1 資料會以 warning 方式呈現，例如：

- 檔名 ID 與 `APCS Title` 中的 ID 不一致
- 缺少 tags
- 缺少 complexity

只有真正損壞學習資料的問題才會讓 CI fail。

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
