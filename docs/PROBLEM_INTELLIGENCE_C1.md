# v2.4 C1｜題目智慧最小可用版本

狀態：**實作契約**

「題目智慧」是把外部 OJ 題目整理成可搜尋、可分類、可後續產生教材的資料層。

它不是新的 Online Judge，也不是第二份 Problem Bank。

## 1｜C1 的最小流程

```text
外部題目網址
→ 正規化來源與題號
→ 去重
→ L0 已索引
→ 來源資料補全
→ L1 AI 候選分類
→ CANDIDATE / NEEDS_QA
```

C1 到此為止。

完整教學、提示、解答、測資與差分驗證屬於 C2。

## 2｜ZeroJudge 第一版

目前正式支援：

```text
https://zerojudge.tw/ShowProblem?problemid=d050
```

不同大小寫、`www`、額外 query parameter 會正規化為：

```text
source       = zerojudge
external_id  = d050
canonical    = https://zerojudge.tw/ShowProblem?problemid=d050
identity     = zerojudge:d050
```

目前 C1 遇到其他 OJ 會明確拒絕，不猜測 identity。

後續來源要逐一新增 parser 與測試。

## 3｜資料位置

```text
data/problem_intelligence/
  zerojudge/
    d050.json
```

一題一檔，方便：

- Git diff；
- 批次更新；
- 逐題驗證；
- 不需要新增資料庫服務。

## 4｜L0 已索引

L0 只需要可靠的來源 identity。

可逐步補：

- title；
- 題意摘要；
- constraints；
- metadata source。

不要求學習者填表。

平常預期由 ChatGPT 讀取來源後批次補全。

## 5｜L1 已分類

L1 使用 AI 候選分類，可包含：

- Primary Skill candidate；
- supporting Skill candidates；
- difficulty candidate；
- prerequisite candidates；
- expected complexity candidate；
- role candidate；
- alternate solution risk candidate；
- evidence suitability candidate；
- rationale。

### 自動 fail-closed

分類結果不能自行指定狀態。

系統以 deterministic rule 決定：

```text
confidence >= 0.80
+ Primary Skill 存在
+ difficulty 存在
+ 無 ambiguity
→ CANDIDATE

否則
→ NEEDS_QA
```

即使是 `CANDIDATE`：

```text
runtime_eligible = false
```

所以不能直接成為 Published Curriculum 或正式 Evidence 題。

## 6｜最小指令

### 匯入一題

```text
python -m tools.problem_intelligence import "https://zerojudge.tw/ShowProblem?problemid=d050"
```

### 批次匯入

```text
python -m tools.problem_intelligence import --file urls.txt
```

文字檔每行一個網址。

### 驗證

```text
python -m tools.problem_intelligence validate
```

另外：

```text
python tools/apcs.py validate
```

也會一起驗證題目智慧資料，因此不需要學習者額外記得另一套 QA 流程。

## 7｜低摩擦原則

實際日常預期不是叫學習者執行上述工程指令，而是：

```text
你：
「把這 50 題 ZeroJudge 加進題庫」

ChatGPT：
讀取 / 整理
→ batch import
→ L0 metadata
→ L1 classification
→ 回報少量真正需要人工確認的 Needs QA
```

只有分類歧義真的會影響學習用途時才詢問。

## 8｜C1 不做

- 不複製完整第三方題庫；
- 不建立大型 crawler service；
- 不建立向量資料庫；
- 不建立新的 learner dashboard；
- 不產生 L2 完整教學；
- 不修改 REC / EV；
- 不產生 learner Evidence；
- 不修改 Cloudflare Worker #58。

這些限制是刻意的，避免題庫系統在有學習價值以前先變成大型工程專案。
