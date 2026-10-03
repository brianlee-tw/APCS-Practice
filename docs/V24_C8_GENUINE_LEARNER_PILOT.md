# v2.4 C8｜真實學習者試用

C8 不驗證「功能能不能跑」，而是驗證這套系統在真實使用下是否真的幫助學習，而且沒有把操作成本拉高。

## 原則

- 不建立新的大型試用表單。
- 不要求一次完成全部項目。
- 只使用真實學習活動；system test、工程假資料、為了過 Gate 刻意製造的失敗都不算。
- 既有 v2.3 Production 繼續正常使用；C8 未完成不代表系統失效。
- 在 C8 完成前，`LEARNER_READINESS = NOT_ASSESSED`。

## 最小試用方式

平常直接用：

```text
Ctrl+Alt+A
→ 今日學習 / 題目庫 / 考試模式
```

不需要另外維護資料。

系統需要在真實使用中逐步取得下列 evidence：

| 項目 | 真實驗證條件 |
| --- | --- |
| Today v2 | 至少實際完成一次 Today 流程 |
| 題目庫 | 至少從題目庫找一題並開始真實作答 |
| Repair | 真實 FAIL / PARTIAL 發生後才使用；沒有失敗時不強迫產生 |
| Transfer | 對新題或延遲冷題進行，不先看方法 |
| Exam | 至少完成一次短時限 mixed practice |
| A0 Evidence | 至少有真實 independent A0 attempt |
| delayed / transfer Evidence | 必須來自真正延遲或新題，原題看答案後重做不算 |
| friction | 只記錄真正讓操作變麻煩的地方 |

## C8 不做

不在這一階段調整 memory policy。C8 的資料先累積；只有進入 C9 後，才允許用足夠真實 Evidence 做離線比較與 policy calibration。

也不因為一次成功或一次失敗就改課程、改 Skill taxonomy、或建立永久弱點。
