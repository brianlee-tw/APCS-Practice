# APCS-Practice

APCS 實作練習、複習與弱點追蹤倉庫。

這個倉庫的 v2.2 設計將題目 metadata 與 solution code 分離：`data/problems.csv` 管理題目資料，`data/solutions.csv` 管理解答檔案與複雜度；資料夾只代表檔案位置，不再是能力分類或進度來源。

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

- **今日複習**：查看並開啟已到期或逾期的題目。
- **完成題目**：首次 AC 後記錄 Recall 與解題分鐘數。
- **複習題目**：記錄 AC / WA / TLE / RE / MLE / CE、Recall 與分鐘數。
- **題目筆記**：建立或開啟 `notes/<id>.md`。
- **檢查與提交**：檢視 Git 變更、stage、commit，以及確認後 push。

Recall 自評：

| Recall | 定義 | 基礎複習間隔 |
| ---: | --- | ---: |
| 0 | 幾乎不會／需要看答案 | 1 天 |
| 1 | 需要提示 | 3 天 |
| 2 | 可獨立完成但偏慢 | 7 天 |
| 3 | 流暢、獨立完成 | 30 天起 |

正式 Review 若連續在不同日期取得 `AC + Recall 3`，間隔依序延長為 30、60、90 天。

分鐘數屬於每次 Finish / Review 的事件資料，可略過；不會覆蓋先前的練習時間紀錄。

### CLI

控制中心是日常入口；CLI 保留給除錯、自動化與進階操作，例如：

```bash
python tools/apcs.py today
python tools/apcs.py finish b130 2 --minutes 18
python tools/apcs.py review b130 1 --result WA --minutes 11
python tools/apcs.py note b130
python tools/apcs.py validate
python tools/apcs.py sync
```

v2.2 以 `data/problems.csv` 與 `data/solutions.csv` 作為靜態 metadata 的唯一正式來源；solution code 不再承載 `APCS` metadata header，也不再提供 source-header fallback。

<!-- APCS_DASHBOARD_START -->
## APCS Training Dashboard

| 指標 | 數量 |
| :--- | ---: |
| 索引題目 | **58** |
| 明確 AC | **0** |
| Mastered | **0** |
| 今日到期複習 | **0** |

### 能力分布

| 領域 | 題數 | AC | 到期 |
| :--- | ---: | ---: | ---: |
| Fundamentals / Simulation | 22 | 0 | 0 |
| Math | 20 | 0 | 0 |
| Arrays / Simulation | 7 | 0 | 0 |
| String | 5 | 0 | 0 |
| Prefix / Greedy | 2 | 0 | 0 |
| Data Structures | 1 | 0 | 0 |
| Search / Sort | 1 | 0 | 0 |

### 今日複習優先序

| ID | 題目 | 領域 | Recall | 到期日 |
| :--- | :--- | :--- | ---: | :---: |
| — | 目前沒有到期題目 | — | — | — |

完整題庫見 [Problem Index](./docs/PROBLEM_INDEX.md)，複習佇列見 [Review Queue](./docs/REVIEW_QUEUE.md)。
<!-- APCS_DASHBOARD_END -->

## 資料來源與可信度

- `data/problems.csv`：題目 ID、名稱、來源、難度與 tags。
- `data/solutions.csv`：solution 路徑、語言與 complexity。
- `data/progress.csv`：目前學習狀態（首次完成、最近 Review、Result、Recall）。
- `data/reviews.csv`：Finish / Review 的 append-only 事件歷史。
- `notes/<id>.md`：可選的 repo 內短筆記。

## 自動化

- Pull Request / main push：Catalog、learning data 驗證；新改動的 C++ / Python 解答做語法編譯檢查。
- main 更新後：安全地重新產生 README、Problem Index、Review Queue。
- 自動同步只 stage 生成檔，不再使用 `git add .`，也不再 `git pull --rebase`。

## Historical folders

`01_Basic_Syntax_Optimization`、`02_Data_Structures`、`03_Algorithmic_Paradigms`、`04_Graph_Theory_and_Advanced_Topics` 是 v1 歷史資料夾。v2 不再用它們當作能力分類或固定「50 題」進度 KPI。

## License

MIT License。
