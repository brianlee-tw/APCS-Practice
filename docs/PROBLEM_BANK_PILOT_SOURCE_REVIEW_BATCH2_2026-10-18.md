# Problem Bank Pilot｜第二批官方題目來源審核

**日期：** 2026-10-18  
**狀態：** `SOURCE_REVIEW_STAGED_NOT_PUBLISHED`  
**範圍：** 已有的 18 題 Pilot 中，另外 5 題的官方來源內容、官方 examples 與 ChatGPT 分類候選  
**來源：** CSES / Codeforces 官方 Problem Set（2026-10-18 核對）  
**安全界線：** 不動 Published/Notion，不新增 learner Evidence，不進現有 L0（目前僅 ZeroJudge），不自動在 Test Center 暴露這批 cases。

## Source review matrix

| PB UID | 官方題目 | Published Role / Primary | Constraints 核心 | 官方範例數 | Output 判定 |
| --- | --- | --- | --- | ---: | --- |
| PB-42 | [CSES Repetitions](https://cses.fi/problemset/task/1069) | Core Independent / S07_String | n ≤ 1,000,000；ACGT 字串 | 1 | EXACT_OUTPUT |
| PB-150 | [CSES Increasing Array](https://cses.fi/problemset/task/1094) | Core Independent / S01_IO | n ≤ 200,000，x_i ≤ 10^9，64-bit 累加 | 1 | EXACT_OUTPUT |
| PB-40 | [CSES Weird Algorithm](https://cses.fi/problemset/task/1068) | Guided Drill / S03_Loops | 初值 n ≤ 10^6；中途可能超過 32-bit | 1 | EXACT_OUTPUT |
| PB-103 | [CF Interesting drink](https://codeforces.com/problemset/problem/706/B) | Guided Drill / S10_Binary_Search | n,q ≤ 100,000；重複門檻查詢 | 1 | EXACT_OUTPUT |
| PB-109 | [CF Less or Equal](https://codeforces.com/problemset/problem/977/C) | Core Independent / S09_Sorting | n ≤ 200,000，0 ≤ k ≤ n，允許 duplicate | 2 | VALIDATE_ANY_CORRECT_X |

所有官方 examples 的 input/output 轉錄為 `data/problem_pilot/source_reviews_batch2.v1.json`，其中包含短摘要、constraints、ChatGPT Primary/Supporting Skill 候選、role/difficulty、QA 理由和來源網址。

### 分類與題型品質

- **PB-42**：String 的單次線性掃描，適合冷測長字串索引、streak 初始化、最大值更新。
- **PB-150**：Primary S01_IO 看似與 Greedy 不一致，但 Published training_purpose 明確把它用於 `L-FND-04` 的 scalar streaming、`long long` 與不必要儲存的避免。新增 S11_Greedy 作 **AI supporting 候選**，不擅自重分類。
- **PB-40**：迴圈分支與每輪狀態更新；不得因起始 n 上限小就把所有中間值當成 int 安全。
- **PB-103**：排序後 binary search/upper_bound 合理，然而 Published 的 U-BIN 對應本來標示 provisional；另有 bounded-frequency / prefix-count 解法，應維持方法歧義提醒。
- **PB-109**：官方要求輸出「任一」合法 x，故 sample output 6 不是唯一答案（例如 5 也合法）；exact-output Test Center 會產生 **false negative**。必須先做 per-problem semantic checker，對每一個候選 x 檢查範圍與「恰好 k 個元素 ≤ x」，對 -1 檢查真正不可行。此批**禁止**將官方 example 當一般 equality testcase。

### Validation and limitations

`python3 tools/pilot_source_review.py`（read-only）驗證：
- Published / Seed PB UID、官方題目 ID、URL、標題、原 role/difficulty/primary skill 和 Schema；
- 合法的 Skill taxonomy 與保守 QA 狀態；
- 四種單一輸出題的官方例子與獨立 Python reference 一致；
- CF 977C 使用 semantic checker，接受等效不同答案並正確拒絕不可行輸出；
- `l0_import_supported=false`、`test_center_status=STAGED_DO_NOT_LOAD`、`ai_approved=false`、`published_mutation=false` 等不可逾越的信任界線。

`tests/test_pilot_source_review.py` 對錯誤官方 sample、來源掉包、冒充 L0/published、CF 977C 變成 exact comparison 等加入回歸；既有 `tools/pilot_release_preflight.py` 也讀取本批並 fail closed。

**不是已完成的工作：** 網頁原始 byte/checksum 沒有封存（`NOT_CAPTURED`）；非 ZeroJudge 的 production L0 importer 尚未完成；真實 OJ 判題、使用者 VS Code 實機操作、L1 人工採納、更多 oracle 差分測資均未完成。

## 剩餘 Pilot 9 題：下一批的執行順序

| 優先 | PB UID | 來源 | 操作原則 |
| --- | --- | --- | --- |
| P1 | PB-164 / PB-165 | Custom／程式識讀、除錯 | 從 Notion/hosted lesson 的原始任務確認題型；不得套用 OJ exact checker |
| P1 | PB-160 / PB-161 | Custom／Complexity | 同上，重點是 constraints、 reasoning 與解釋型答案 |
| P1 | PB-169 | Custom／Struct/Sorting | 確認多鍵排序 tie-break 和穩定性契約 |
| P2 | PB-120 | APCS / ZeroJudge q836 | 核實原始 APCS 年度、題意、sample，不能只信題名 |
| P2 | PB-97 | Codeforces 71A | 官方來源核實後可轉進固定輸出題 staging |
| P3 | PB-10 / PB-32 | ZeroJudge q182 / a233 | 原始題頁尚不能可靠取得完整 sample；維持 PENDING 不推測 |

不為清空待辦而大規模生成 AI tests 或完整解答。進 Test Center 前需要正確的 judge identity adapter、官方 sample 及符合題型的 checker；人工 learner Evidence 仍必須是真實練習結果。
