# APCS-Practice

APCS 實作練習、複習與弱點追蹤倉庫。

這個倉庫的 v2 設計把「**檔案放在哪個資料夾**」和「**這題屬於什麼能力**」分開：題目能力由 `APCS Tag`、題名與檔名自動分類；舊有四個資料夾只保留歷史位置，新題目建議統一放在 [`solutions/`](./solutions/)。

## 目標

- APCS 觀念題與實作題持續提升。
- 不以「刷了幾題」取代真正的掌握程度。
- 將 **AC、重解結果、複習間隔、弱項** 變成可追蹤資料。
- 保留既有 Notion 筆記，但不再要求每題都開一頁 Notion。

## 最短工作流程

1. 在 `solutions/` 新增 `.cpp` / `.py`，檔名以題號開頭，例如 `b130_Random_Number.cpp`。
2. 檔頭只保留相對穩定的題目資訊：
   ```cpp
   // APCS Title: b130. 明明的隨機數
   // APCS Complexity: O(N log N)
   // APCS Tag: Sorting, Set
   // APCS Difficulty: 1
   // APCS Source: https://...
   ```
3. AC 後執行：`python tools/apcs.py finish b130 2`
4. 之後重解執行：`python tools/apcs.py review b130 3`
5. 只有值得整理的題目才執行：`python tools/apcs.py note b130`

Recall 自評：`0=不會`、`1=需要提示`、`2=自己做出但偏慢`、`3=流暢獨立完成`。

更完整的操作方式見 [`docs/WORKFLOW.md`](./docs/WORKFLOW.md)。

<!-- APCS_DASHBOARD_START -->
> Dashboard 將由 `python tools/apcs.py sync` / GitHub Actions 自動產生。
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
