# APCS-Practice

APCS 實作練習、複習與弱點追蹤倉庫。

這個倉庫的 v2 設計把「**檔案放在哪個資料夾**」和「**這題屬於什麼能力**」分開：題目能力由 `APCS Tag`、題名與檔名自動分類；舊有四個資料夾只保留歷史位置，新題目建議統一放在 [`solutions/`](./solutions/)。

## 目標

- APCS 觀念題與實作題持續提升。
- 不以「刷了幾題」取代真正的掌握程度。
- 將 **AC、重解結果、複習間隔、弱項** 變成可追蹤資料。
- 保留既有 Notion 筆記，但不再要求每題都開一頁 Notion。

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

目前 v2.1 仍可讀取既有 solution 檔案中的 `APCS Title`、`APCS Tag`、`APCS Complexity` 等 metadata。新的 Problem Catalog 與 metadata workflow 將在後續版本處理；本版不大量重寫既有 solution files。

<!-- APCS_DASHBOARD_START -->
## APCS Training Dashboard

| 指標 | 數量 |
| :--- | ---: |
| 索引題目 | **57** |
| 明確 AC | **0** |
| Mastered | **0** |
| 今日到期複習 | **0** |
| 舊制完成（未確認 AC） | **44** |

> `📚 Legacy` 代表舊制資料；Notion 筆記本身不等同於 AC。

### 能力分布

| 領域 | 題數 | AC / 舊制完成 | 到期 |
| :--- | ---: | ---: | ---: |
| Fundamentals / Simulation | 21 | 12 | 0 |
| Math | 20 | 17 | 0 |
| Arrays / Simulation | 7 | 7 | 0 |
| String | 5 | 5 | 0 |
| Prefix / Greedy | 2 | 2 | 0 |
| Data Structures | 1 | 0 | 0 |
| Search / Sort | 1 | 1 | 0 |

### 今日複習優先序

| ID | 題目 | 領域 | Recall | 到期日 |
| :--- | :--- | :--- | ---: | :---: |
| — | 目前沒有到期題目 | — | — | — |

完整題庫見 [Problem Index](./docs/PROBLEM_INDEX.md)，複習佇列見 [Review Queue](./docs/REVIEW_QUEUE.md)。
<!-- APCS_DASHBOARD_END -->

## 資料來源與可信度

- `data/progress.csv`：目前狀態（Verdict、初次 AC、最近複習、Recall）。
- `data/reviews.csv`：每次複習的 append-only 歷史。
- 程式碼檔頭：題目名稱、複雜度、Tags、難度、來源等靜態 metadata。
- `notes/<id>.md`：可選的短筆記。
- 既有 `APCS Note: <Notion URL>` 會繼續顯示，但 **Notion 連結不再等同於 AC**。

## 自動化

- Pull Request / main push：metadata 驗證；新改動的 C++ / Python 解答做語法編譯檢查。
- main 更新後：安全地重新產生 README、Problem Index、Review Queue。
- 自動同步只 stage 生成檔，不再使用 `git add .`，也不再 `git pull --rebase`。

## Legacy folders

`01_Basic_Syntax_Optimization`、`02_Data_Structures`、`03_Algorithmic_Paradigms`、`04_Graph_Theory_and_Advanced_Topics` 是 v1 歷史資料夾。v2 不再用它們當作能力分類或固定「50 題」進度 KPI。

## License

MIT License。
