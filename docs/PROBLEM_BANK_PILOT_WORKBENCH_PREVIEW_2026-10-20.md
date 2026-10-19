# 題庫 Pilot｜Stage I｜跨平台官方範例 Workbench Preview

**日期：** 2026-10-20  
**PR：** [#89](https://github.com/brianlee-tw/APCS-Practice/pull/89) · `feat/problem-bank-pilot-20261018`  
**狀態：** 工程測試通過；**僅 PR 分支 Preview**，尚未合併 main，未進行本人本機 VS Code 實機驗收。  
**權威：** Published Curriculum 的 PB / Placement 定位不變；題面與官方範例對應原始 OJ，並經既有 source-review staging 核對。

## 1. 這一輪真正接入的內容

| PB UID | 題目 | Judge-local source/ID | 官方 Fast 樣例 | Published 定位 |
| --- | --- | --- | ---: | --- |
| PB-42 | [CSES Repetitions](https://cses.fi/problemset/task/1069) | `cses/1069` | 1 | S07 String / Core Independent |
| PB-150 | [CSES Increasing Array](https://cses.fi/problemset/task/1094) | `cses/1094` | 1 | S01 IO / Core Independent |
| PB-97 | [CF 71A Way Too Long Words](https://codeforces.com/problemset/problem/71/A) | `codeforces/71A` | 1 | S07 String / Worked Example |
| PB-120 | [APCS / ZeroJudge q836 小心陷阱](https://zerojudge.tw/ShowProblem?problemid=q836) | `zerojudge/q836` | 2 | S23 Simulation / Core Independent |
| **總計** | **4 題** | | **5 組** | |

這五組公開官方樣例放在 `data/problem_enrichment/<judge>/<id>/tests.json`，每組皆為：

```text
provenance = OFFICIAL
trust = OFFICIAL
suite = fast
visibility = official
```

沒有把 ChatGPT 猜測的測資標成 Official，沒有對這批題目新增 **Full** edge cases，也沒有宣告外部 OJ AC。

## 2. 身分綁定與防誤載

`tools/vscode_task.py` 的 `PILOT_PREVIEW_IDENTITIES` 顯式白名單只包含上述四筆。Workbench 使用正式 Published scratch filename 解析 Placement、PB UID 與 Judge 來源，再從官方題目網址決定是否允許開啟對應本地 bundle。

- `CSES-1069` → `cses/1069`，`CSES-1094` → `cses/1094`。
- `CF-71A` → `codeforces/71A`，保留 Judge 端題號大小寫。
- `APCS-ZJ-q836` → `zerojudge/q836`。Published 來源為 APCS，但實際 OJ 位於 ZeroJudge。
- 必須同時一致：Published source、namespaced problem ID、PB UID、canonical URL、bundle.source、bundle.external_id、bundle.canonical_url。
- 不會替其他 CSES / CF / APCS 題自動猜測來源或剝除字首；錯題網址、缺網址、假來源、換 PB UID 及未經 Publisher 認可的資料會 fail closed。
- 固定輸出樣例由現有 TestAssetStore / local exact comparison 管理；不會把 `CF 977C` 的特殊多解題錯用成 exact-output。
- `q182` 官方題面／sample 尚未直接驗證，`a233` 來源有正整數／0 樣例歧義；兩者均不在這次 Preview。
- Custom PB-160/161/164/165/169 仍在 Notion Lesson Contract 層級，逐題 Hosted Task 未取得；也不在此 Preview。

## 3. QA、回歸與發布限制

- `data/problem_pilot/workbench_preview.v1.json` 保存明確的四筆允許清單、五組官方樣例數、來源檔案、類型、信任狀態和 `BLOCKED_MANUAL`。
- `tests/test_pilot_workbench_preview.py` 會走正式 Published scratch → `problem_context` → `_test_bundle` → `_visible_cases`，確認四題身份匹配、Case 數與 Practice / Transfer / Exam 作答前可見性。
- `tools/pilot_workbench_preview.py` 讀取前兩批 source-review staging 與真實 `TestAssetStore`，逐組比較 input/output，拒絕 URL/PB identity 掉包、未審核來源、Generated Cases 和冒充 Published。
- `tests/test_pilot_workbench_preview_manifest.py` 含負向回歸。
- `tools/pilot_release_preflight.py` 現在另回報 `workbench_official_preview_problems=4`、`workbench_official_preview_samples=5`、`workbench_total_official_samples=13`；先前首批 8 組官方範例、17 組差分 edge cases 保持原數字及權限。
- 本次核心程式與 QA 測試完成後 **APCS Validate #322 PASS**；本文件提交後仍需核對最新 HEAD CI。

## 4. 尚未完成，不可提前宣稱

- 真實 Windows / WSL / VS Code 的 `Ctrl+Shift+B`、實際編譯與 learner 誤答／修正的 UI 操作；
- 四題的 OJ hidden test 接受率、全 constraints 的完整測試覆蓋；
- 本批四題的新差分 Full edge cases；
- 其他 staging 題的 judge identity adapter、CF 977C semantic checker 正式接入；
- learner OJ 判定、Attempt / Evidence、Transfer、Delayed cold test 或 Readiness。
  
這些都不能由 Mock + CI 直接推論。**C8 仍 OPEN、LEARNER_READINESS 仍 NOT_ASSESSED。** PR #89 保持 **Draft**；不得自動合併，也不能改寫 Notion 正式題庫、Published 或本機既有 learner state。

## 5. 下個合理關卡

如果要繼續擴充，先在官方可核對的固定輸出題上增加少量高價值 **candidate-only** 邊界測資，使用兩個獨立 oracle 實際驗證後再存 Full。尤其 CSES Increasing Array 應驗證 `long long` 累加、APCS q836 應檢驗兩陷阱同時觸發與終止次序；不可將 candidate output 自行標成 Official。後續還需真實手動 Test Center 驗收與明確合併授權。

本批未使用 API，ChatGPT 只負責來源核對與測資／QA 工程，沒有授予任何 learner mastery。
