# 深度教學資料（v2.4 C2）

這個資料夾只保存少量高價值題目的 **L2 教學資料**。

它不是第二份題庫，也不是 learner-facing 管理介面。

## 一題的結構

```text
data/problem_enrichment/
  zerojudge/
    d050/
      package.json
      solution.cpp
      oracle.cpp   # 只有差分驗證需要時才存在
```

`package.json` 保存：

- 問題模型；
- 關鍵觀察；
- 正確性推理；
- 不變量；
- 時間 / 空間複雜度；
- 常見陷阱；
- 邊界情況；
- A1–A5 提示；
- 替代方法；
- 遷移辨識訊號；
- 官方 sample；
- 少量 generated case；
- 驗證狀態。

## 可信度不是「AI 說正確」

解答可信度只能由實際驗證往上升：

```text
AI_CANDIDATE
→ COMPILE_VERIFIED
→ SAMPLE_VERIFIED
→ DIFFERENTIAL_VERIFIED
→ OJ_ACCEPTED
```

含義：

- **AI_CANDIDATE**：AI 產生，尚未驗證。
- **COMPILE_VERIFIED**：本機 C++ 編譯成功。
- **SAMPLE_VERIFIED**：官方 sample 全部通過；仍不代表完整正確。
- **DIFFERENTIAL_VERIFIED**：和可信 brute-force / oracle 在指定 generated cases 一致。
- **OJ_ACCEPTED**：有外部 OJ AC reference。

## 只在需要時產生

L2 不對所有題批量生成。

只有：

- Today 即將使用；
- Lesson 缺 teaching-ready 題；
- Transfer / Exam pool 需要；
- learner 主動要求；
- 人工 curation 判定高價值；

才值得產生。

這是刻意的成本控制與 anti-overengineering 設計。
