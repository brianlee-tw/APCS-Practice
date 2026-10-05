# 題目 Enrichment 與本地測資（v2.4）

這個資料夾只保存少量高價值題目的**附屬教學與驗證資產**。

它不是第二份題庫，也不是 learner-facing 管理介面。Problem identity 仍由既有 Problem Intelligence / Published Curriculum / Catalog authority 提供。

## 一題的結構

~~~text
data/problem_enrichment/
  zerojudge/
    d050/
      tests.json       # 可獨立存在
      package.json     # 舊版 / L2 深度教學 package；可選
      solution.cpp     # trusted reference；有需要才存在
      oracle.cpp       # 差分驗證需要時才存在
~~~

### tests.json

本地 Test Center 的 durable 測資資產。它可以在尚未建立完整 L2 package.json 時獨立存在。

每個 case 至少記錄：

- id
- name
- input
- expected_output（candidate 可為 null）
- provenance
- trust
- suite
- visibility

### Provenance

~~~text
OFFICIAL
AI_GENERATED
MANUAL
ORACLE
~~~

### Trust

~~~text
OFFICIAL
CANDIDATE
ORACLE_VERIFIED
DIFFERENTIAL_VERIFIED
~~~

CANDIDATE 即使帶有 AI 猜測的 expected output，也**不得**影響 learner-facing PASS / FAIL summary。

### Suite

~~~text
fast
full
~~~

- fast：Ctrl+Shift+B 每次執行；應保持很快。
- full：準備 OJ、完成 debug 或 learner 主動按 T 時執行。

### Visibility

~~~text
official
practice
post_attempt
~~~

正式 Transfer / Mock / Exam 在 pre-attempt 階段只允許 official cases；generated edge / oracle cases 必須在 attempt 後才能解鎖。

## Runtime AI candidates

未驗證、一次性的 AI edge-case candidate 不直接寫入 Git：

~~~text
.apcs/runtime/test_candidates/<source>/<problem-id>/tests.json
~~~

它們只供 curation / verification 使用，不影響 PASS。

只有經 oracle / differential / 人工可靠驗證後，才適合提升為 durable data/problem_enrichment/.../tests.json。

## 舊 package.json 相容

既有 L2 package.json 仍可保存：

- 問題模型
- 關鍵觀察
- 正確性推理
- 不變量
- 時間 / 空間複雜度
- 常見陷阱
- A1–A5 提示
- 官方 sample
- generated cases
- 驗證 receipt

Test Center loader 會在沒有 tests.json 時 fallback 讀取舊 package.json 的官方 sample，因此不需要 destructive migration。

## 外部 OJ 仍是 verdict authority

~~~text
Local Test PASS
≠
OJ AC
~~~

本地測資只用於快速回饋、debugging 與 regression。不得因 local PASS 自動建立 Attempt PASS、Mastery、RR/IR readiness 或 Evidence。

## 只在需要時產生

不對所有題批量生成 edge cases。

只有：

- Today 即將使用
- learner 正在 debug
- Lesson 缺 teaching-ready 測資
- Transfer / Exam postmortem 需要
- 人工 curation 判定高價值

才值得新增 durable tests。

這是刻意的 learner-friction / maintenance-cost 控制。
