# 題目智慧資料區

這個資料夾保存 v2.4「題目智慧」的 **L0 已索引**與 **L1 已分類候選**資料。

## 這裡不是什麼

- 不是第二份 Problem Bank。
- 不是 Published Curriculum。
- 不是 learner Evidence。
- 不是自建 Online Judge。
- 不是第三方 OJ 題面鏡像。

正式 Problem identity / placement 仍由既有 Problem Bank 與 Published Curriculum 管理。

## 一題一個 JSON

路徑：

```text
data/problem_intelligence/<source>/<external_id>.json
```

例如：

```text
data/problem_intelligence/zerojudge/d050.json
```

同一題不同形式的 ZeroJudge URL 會正規化成同一個 identity：

```text
zerojudge:d050
```

## L0｜已索引

只保存低成本、可靠取得的資料：

- 來源；
- 外部題號；
- canonical URL；
- 標題（若可靠取得）；
- 題意摘要（若需要，且不得大量複製第三方完整題面）；
- constraints。

## L1｜已分類

加入 AI 候選分類：

- Primary Skill candidate；
- supporting skills；
- difficulty；
- prerequisites；
- expected complexity；
- role；
- alternate solution risk；
- evidence suitability。

AI 分類永遠只是候選。

系統只會產生：

- `CANDIDATE`；
- `NEEDS_QA`。

它不能直接把題目升成 Published，也不能建立 learner Evidence。

## 最小操作

單題或多題網址：

```text
python -m tools.problem_intelligence import <URL> <URL> ...
```

大量網址可放文字檔，每行一個：

```text
python -m tools.problem_intelligence import --file urls.txt
```

平常預期由 ChatGPT 幫忙批次整理，不要求學習者手動維護 JSON。
