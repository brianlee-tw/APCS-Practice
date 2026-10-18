# APCS 題庫 Pilot｜Batch 4 最後四題來源核對

**日期：** 2026-10-18  
**分支：** `feat/problem-bank-pilot-20261018`，PR #89（Draft）  
**輸出：** `data/problem_pilot/source_reviews_batch4.v1.json`  
**真實狀態：** 3 題官方來源已核對；1 題僅官方索引身分＋第三方題意，**不宣告四題全部完成官方審核**。

## 來源與樣例驗證結果

| PB UID | 題目 / 官方網址 | 本批來源信任 | 公開官方 sample | 關鍵 QA |
| --- | --- | --- | ---: | --- |
| PB-120 | [ZeroJudge q836 小心陷阱](https://zerojudge.tw/ShowProblem?problemid=q836) | `OFFICIAL_PAGE_REVIEWED` | 2 | APCS 2025-06；跳躍→同時判定兩陷阱→扣血→結束位置 |
| PB-97 | [Codeforces 71A Way Too Long Words](https://codeforces.com/problemset/problem/71/A) | `OFFICIAL_PAGE_REVIEWED` | 1 | **長度嚴格 >10 才縮寫**；Worked Example 不可誤當 A0 Gate |
| PB-32 | [ZeroJudge a233 排序法](https://zerojudge.tw/ShowProblem?problemid=a233) | `OFFICIAL_PAGE_REVIEWED_WITH_QA_FLAG` | 1 | N ≤ 10^6；題文稱正整數，但官方 sample **包含 0**；數值完整上下界未明 |
| PB-10 | [ZeroJudge q182 字串操作](https://zerojudge.tw/ShowProblem?problemid=q182) | `SECONDARY_DESCRIPTION_OFFICIAL_SAMPLE_PENDING` | **0** | ZeroJudge 2025-01 索引確認身分；ShowProblem 抓取只得到登入／空殼；次級解題筆記不足以證明官方完整規格 |

第三方來源僅輔助辨識 q182：例如 [2025/01 APCS 題解](https://hackmd.io/%40HyC-1029/r1p2knkTxg) 描述雙字元交換／排序／兩半交錯操作，並指出偶數長度。這些 **不能標成 Official**，目前不可建立官方測資包或正式教學-ready 結論。

## 題目與分類品質

1. **PB-120** 已核對官方 k、x1/x2、y1/y2 取值界線及位置／血量狀態更新順序，Primary `S23_Simulation` / Core Independent / D2 合理。它雖具有狀態模擬題特徵，但只是 AI Candidate，還沒有人類解題實績。
2. **PB-97** Primary `S07_String` / D1 / Worked Example；可建立長度 10 與 11 邊界的分類 QA。正式 Worked 不能與 independent mastery 混淆。
3. **PB-32** Primary `S09_Sorting` / D2 / Guided Drill，最多 10^6 個數；比較排序的合理目標為 (O(n\log n))。官方題文不一致應保留 `SOURCE_POSITIVE_INTEGER_VS_ZERO_SAMPLE`，不能猜定輸入只含正整數。
4. **PB-10** Primary `S07_String` / D2 / Guided Drill 只是和 Published 的候選一致；因缺官方完整題面和 sample，候選 Confidence 降低且暫停進一步 Test Center 產製。

## 新增的自動 QA

- `tools/pilot_final_four_source.py`：只讀檢查 Published ↔ Pilot PB UID、正式 URL、judge、source status、sample counts、候選分類、QA Flags；另用小型獨立 reference 核對 **4 組官方 sample I/O**。
- `tests/test_pilot_final_four_source.py`：驗證 q836 兩種扣血條件、CF 71A 長度 10/11、a233 0/重複值、錯誤範例及來源身分掉包。
- `tools/pilot_release_preflight.py`：納入 Batch 4 的來源狀態；拒絕把 q182 sample 或題面冒充官方已核對。
- `tests/test_pilot_release_preflight.py`：以偽造 q182 官方 sample 的負向測試確認 **engineering FAIL / release BLOCKED_MANUAL**。

上述測試只說明來源紀錄一致及樣例符合檢查邏輯，**不宣稱外部 OJ hidden tests AC**，也不修改 L0/L1、Published Curriculum、Notion 或 learner Evidence。

## Pilot 18 題覆蓋盤點

| 類別 | 題數 | 可信度／發布狀態 |
| --- | ---: | --- |
| ZeroJudge 首批完整來源 + 官方範例及加強測資 | 4 | 有 8 官方樣例、17 差分驗證 edge cases；仍未人工 learner acceptance |
| 第二批 CSES / CF 來源 staging | 5 | 官方來源摘要及樣例已記錄；未接正式 L0/Run |
| 第三批 Custom 正式 Notion Lesson Contract | 5 | Lesson/Rubric 已核，但逐題 Hosted task instance 未取得 |
| 本批可核對官方來源 | 3 | Source-reviewed staging，4 組官方 sample，未正式接 Test Center |
| 本批 q182 | 1 | 官方完整題面與官方範例待核；僅保留未驗證的次級描述 |
| **總計** | **18** | **18 筆均有各自的 QA 狀態，不等於 18 題都可正式練習** |

## 剩餘工程關卡

1. **PB-10 / q182**：取得可直接驗證的官方完整題面與官方 sample，否則繼續 `SOURCE_PENDING`；不要由第三方貼文生成冒充官方的 I/O。
2. **Custom 5 題**：按 Notion 已定義的 Reading/Implementation/Hosted-OJ 流程取得逐題任務封包；不得一律套上 exact-output judge。
3. **CSES / Codeforces 及 APCS sources**：若要進 Learner Workbench，先確認 judge-local identity adapter、oracle 與 preattempt 防劇透，不可直接重用 ZeroJudge-only L0 importer。
4. **正式合併與 C8**：維持 `BLOCKED_MANUAL`，待用戶明確同意且完成真實 VS Code acceptance；不能靠 CI 判斷 learner readiness。

**未做任何付費 API 呼叫；ChatGPT 只做候選審核。**
