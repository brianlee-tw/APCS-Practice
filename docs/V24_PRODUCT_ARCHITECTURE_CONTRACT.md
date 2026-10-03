# APCS C++ Learning System v2.4｜產品與架構契約

狀態：**規劃契約 v1｜已核准進入設計／實作階段，但尚未改變 v2.3 production authority**

版本目標：**低摩擦認知式學習系統**

> 本文件是 v2.4 的產品與架構上位契約。它的目的不是增加功能數，而是讓學習者以更少操作、更少管理成本，取得更高的獨立解題、遷移、除錯與考場效率。
>
> 核心產品原則：**系統負責管理學習；學習者負責真正學習。**

---

## 0｜名詞與閱讀方式

本文件盡量使用中文。第一次出現的重要專有名詞如下：

- **唯一正式資料來源（SSOT, Single Source of Truth）**：某類資料只有一個正式權威來源，避免多套資料互相矛盾。
- **核心功能（Core）**：v2.4 必須完成，否則版本不算完成。
- **可選功能（Optional）**：只有在證明能提升學習效果或效率時才實作，不阻塞 v2.4。
- **明確不做（Non-goals）**：即使技術上可行，也不列入 v2.4，避免過度工程化。
- **題目智慧（Problem Intelligence）**：從外部 OJ 題目取得、整理、分類、驗證並產生教學用途資料的系統；它不是新的 OJ，也不是第二份 Problem Bank。
- **學習者摩擦預算（Learner Friction Budget）**：限制日常操作、填寫、設定與管理成本，確保系統不搶走真正學習時間。
- **階段關卡（Gate）**：每一階段必須達成的可驗證條件。未過關不得假裝下一階段已完成。
- **遷移（Transfer）**：把能力用到新的題目、不同表面情境或新的方法辨識情境，而不是重做原題。
- **交錯練習（Interleaving）**：把容易混淆的題型或策略混合安排，要求學習者先辨認方法，而不是看到同類題連續出現就套模板。
- **引導淡出（Guidance Fading）**：隨能力提升逐步減少提示與範例，最後回到無提示獨立作答。
- **後設認知（Metacognition）**：學習者對「自己是否會、信心有多高」的判斷；這和實際能力是不同訊號。
- **認知編排器（Cognitive Orchestrator）**：v2.4 中負責決定「下一個最值得做的學習活動」的決策層。

---

# 1｜版本定位

v2.3 已完成可靠的學習基礎設施：

```text
課程
→ Published Curriculum
→ VS Code Learning Runtime
→ Attempt
→ Evidence
→ Skill × Track Memory
→ Today
→ Remote Writeback
→ REC / EV
```

v2.4 不重寫這套底層，而是在其上增加兩個智慧層：

```text
外部題目來源
      ↓
題目智慧
      ↓
高品質題目 / 教學素材 / 練習候選
      ↓
認知編排器
      ↓
Today / Repair / Transfer / Exam
      ↓
真實作答
      ↓
Evidence
      ↓
Learner Model
```

v2.4 的總目標定義為：

> **在固定學習時間內，最大化可持久、可獨立、可遷移的能力成長。**

不是：

- 最大化題目數；
- 最大化教材數；
- 最大化複習數；
- 最大化 dashboard；
- 最大化 AI 生成內容。

---

# 2｜v2.3 底層凍結原則

除非發現 correctness / reliability 缺陷，以下 v2.3 核心架構視為凍結：

## 2.1 Authority 分工

### Notion

用途：

- 課程與長文教材 authoring；
- Problem Bank；
- REC；
- Evidence Ledger；
- 人類可讀的教學與反思資料。

不得成為：

- 第二套即時排程器；
- 第二套 adaptive memory；
- 手動 mastery authority。

### GitHub

用途：

- 已發布 curriculum contract；
- deterministic policy；
- source code；
- tests / CI；
- versioned architecture contract；
- release receipt。

### VS Code Control Center

仍是日常主要操作介面：

- 今日學習；
- 練習；
- 複習；
- Reading；
- Implementation；
- build / run / debug；
- Finish / Review；
- Evidence capture；
- Exam mode。

### ChatGPT

角色：

- 教學；
- 診斷；
- 提示；
- 除錯教練；
- 題目分類與 enrichment；
- 學習活動建議。

不得：

- 自行捏造 learner attempt facts；
- 自行授予 mastery；
- 自行授予 RR / IR readiness；
- 用 AI confidence 取代真實 Evidence。

### Cloudflare

保留：

- browser 真正有價值的教材 / Lab / 視覺化；
- trusted writeback；
- read-only operational views。

不得：

- 維護第二份 adaptive memory；
- 成為第二套 curriculum runtime truth。

---

# 3｜v2.4 的最高產品原則

所有新功能都必須遵守以下順序：

```text
學習價值
> 操作便利
> 時間效率
> Evidence 品質
> 可維護性
> 功能完整度
> 工程炫技
```

任何功能若增加系統複雜度，卻沒有明確提升前四項，不應進 production。

---

# 4｜學習者摩擦預算

這是 v2.4 的硬性產品契約。

## 4.1 啟動摩擦

從開啟 Control Center 到開始第一個今日任務：

- 目標：**不超過 2 個有意義的操作**；
- 不要求先設定一堆 session 參數；
- 進階設定不得阻擋開始學習。

理想流程：

```text
Ctrl+Alt+A
→ 今日學習
→ 開始
```

## 4.2 作答期間

正式解題期間：

- 系統不得主動一直打斷；
- 除非學習者主動要求提示，否則不插入表單；
- 可自動取得的資料一律自動取得。

例如：

- 時間戳記；
- 開啟題目時間；
- build / run 時間；
- 已知的 Judge result；
- Published Placement identity。

不得再問一次。

## 4.3 每題結束

一般題目的 learner-facing 問題：

- 預設最多 **3 個必要 interaction**；
- 若可從 runtime 確定，就降到 0–2 個；
- 失敗時可增加 1 個「主要卡點」選擇，但不展開大型表單。

例如：

```text
Assistance?
Independent?
主要卡點?（只有必要時）
```

Novelty / Activity / Placement / Timed 若可由系統判定，不應要求學習者手填。

## 4.4 每小時管理成本

60 分鐘學習 session 中：

> **管理系統、填資料、設定選項的總時間目標不超過約 3 分鐘。**

這是產品 KPI，不是 learner 的責任。

## 4.5 新欄位准入規則

任何新 learner-facing 欄位必須回答：

> 「這個資料會改變下一個學習決策、Evidence 解讀或 repair 嗎？」

若答案是否定：

**不收集。**

## 4.6 Dashboard 原則

- 不要求學習者每天看 dashboard；
- dashboard 是解釋系統決策，不是另一份待辦；
- 能由 Today 自動處理的問題，不再要求學習者人工管理。

---

# 5｜核心功能（Core）

以下功能全部列入 v2.4 Core。

## 5.1 題目智慧

建立跨 OJ 的題目整理、分類與教學 enrichment 能力。

首要支援：

- ZeroJudge；
- APCS 官方題；
- CSES；
- 後續可加入其他來源。

它解決：

- OJ 分類粗糙；
- 難度不一致；
- 題目與 Skill 關係不清；
- prerequisite 不清；
- 不知道適合 Guided / Core / Transfer / Mock；
- 沒有一致的教學與提示層級。

## 5.2 題目庫瀏覽與自然語言查找

建立「我的題庫」入口，但不做複雜管理後台。

學習者可以：

- 搜尋題目；
- 按 Skill / Unit / Difficulty / Source / 未做 / 已做 / Transfer 篩選；
- 直接用自然語言詢問 ChatGPT。

例如：

> 找一題我沒做過、約 20 分鐘、5+5 程度、DFS/BFS 都可能，但不要透露方法。

## 5.3 防劇透機制

正式依 Activity 控制 learner 可見資訊。

### Guided Drill

可顯示：

- Skill；
- Lesson；
- 方法方向。

### Core Independent

只顯示必要 context。

### Transfer Challenge

不得預先透露：

- Primary Skill；
- 主要演算法；
- key observation；
- 解題分類。

### Mock

更嚴格：

- 不透露 Unit；
- 不透露 Skill；
- 不透露方法；
- 不透露 difficulty 解釋。

## 5.4 提示階梯編譯

Teaching-ready 題可建立：

```text
A1 診斷問題
A2 概念 / 方法方向
A3 核心步驟 / pseudocode
A4 implementation help
A5 完整解法
```

目標：

- ChatGPT 不臨時過度提示；
- 提示內容與 Assistance evidence 一致。

## 5.5 交錯與方法辨識

建立容易混淆的 Skill / Strategy 關係，例如：

- Prefix Sum ↔ Sliding Window；
- Two Pointers ↔ Binary Search；
- DFS ↔ BFS；
- Greedy ↔ DP；
- Brute Force ↔ Backtracking；
- Sorting ↔ Map / Set。

系統可產生「先辨認方法、不一定完整 coding」的短活動：

```text
這題你會選哪個方法？
哪個 constraint 是 signal？
另外兩個方法為什麼不成立？
```

## 5.6 自適應引導淡出

系統依 Evidence 調整 scaffold：

```text
Worked Example
→ Completion
→ Guided Drill
→ Core Independent
→ Transfer Challenge
```

原則：

- FAIL / 高 Assistance：增加支援；
- A2 以下穩定 PASS：逐步減少支援；
- A0 independent PASS：進 independent / transfer；
- Transfer FAIL：先診斷 bottleneck，不直接退回完整解答。

## 5.7 閉環修復系統

錯誤分類不得只做紀錄。

正式流程：

```text
錯誤
→ root cause
→ 最小 repair
→ 新題 transfer
→ delayed retest
```

Repair 依 bottleneck 選：

| Bottleneck | 優先 Repair |
| --- | --- |
| Concept | 最小概念修補 + concept check |
| Condition | valid / invalid contrast |
| Representation | 題意 → state / graph / array |
| Strategy | 方法辨識對照 |
| Complexity | constraint → feasibility |
| Implementation | skeleton reconstruction |
| Syntax / API | 最小 API / syntax repair |
| State / Index | trace + boundary |
| Debugging | minimal failing case |
| Exam Interface | timed decision drill |

## 5.8 Today v2 認知編排

Today 不再只有 Review + New Learning。

候選活動：

- Retention；
- New Learning；
- Repair；
- Discrimination；
- Transfer；
- Exam。

但同一天不要求全部做。

系統根據：

- curriculum route；
- Evidence；
- memory；
- bottleneck；
- recent failure；
- transfer need；
- exam proximity；
- session capacity；

選出少量高價值活動。

## 5.9 Exam Runtime

建立正式考試執行模式：

```text
Scan
→ Choose
→ Solve
→ Compile
→ Submit
→ Debug
→ Stop-loss
→ Switch
→ Final check
```

自動記錄能自動取得的時間點：

- 開題；
- 第一個 plan；
- first compile；
- first submit；
- AC；
- switch；
- end。

Postmortem 只問最少必要資訊，例如主要失分原因：

- 不會；
- 想太久；
- 寫太慢；
- bug；
- 看錯題；
- complexity；
- 時間配置。

## 5.10 Calibration 基礎設施

建立 Memory Policy 的離線校準能力，但不直接上 online ML。

流程：

```text
real delayed evidence
→ predicted retrievability
→ actual outcome
→ offline replay
→ compare policy
→ candidate policy
→ feature flag
→ rollout
```

---

# 6｜可選功能（Optional）

以下列入 v2.4 roadmap，但不阻塞版本完成。

## 6.1 信心校準

只在少量重要 activity sampling：

- Transfer；
- Diagnostic；
- Mock；
- calibration sample。

輸入應極簡，例如：

```text
你覺得能獨立完成嗎？
30% / 60% / 90%
```

用途：

- overconfidence；
- underconfidence；
- learner self-model。

不得：

- 直接影響 mastery；
- 直接提高 readiness。

## 6.2 Mental Effort

「主觀心智負荷」可研究，但預設 OFF。

只在小量 calibration activity 使用 1–5 分，若無明確學習價值，直接刪除。

## 6.3 Misconception Candidate

單次 typo / 粗心不建立長期弱點。

只有：

```text
同 root cause
+
不同題目重現
```

才成為 misconception candidate。

需經 repair + transfer 後再判定是否仍存在。

## 6.4 Learning Status v2

可增加：

- Transfer evidence；
- Hint dependence；
- repeated bottleneck；
- confidence calibration；
- exam execution。

但不建立黑箱總分。

---

# 7｜明確不做（Non-goals）

v2.4 不做：

1. **自建完整 Online Judge**
   - 不自行維護 sandbox；
   - 不自行維護 CPU / memory limits；
   - 不取代 ZeroJudge / CSES / APCS Judge。
   - 外部 OJ 仍是 verdict authority。

2. **黑箱 Mastery Score**
   - 不建立「APCS 能力 87 分」之類無法解釋的總分。

3. **AI 自動授予 readiness**
   - 工程測試不能變 learner evidence；
   - AI confidence 不能變 RR / IR PASS。

4. **大規模 learner forms**
   - 不要求每題填 10–20 欄。

5. **第二份 curriculum**
   - Problem Library 可以很大；
   - Published Curriculum 仍維持既有 52-Lesson 主線，除非未來有真實 coverage evidence 要求修改。

6. **第二份 adaptive memory**
   - Notion / Cloudflare 不再各維護一份 memory truth。

7. **Reading 平行教材線**
   - Reading / Implementation 繼續是 Track，不拆成兩套 curriculum。

8. **AI 大量生成新題作為正式 Evidence**
   - v2.4 主要整理與使用可靠外部題目。
   - AI 可生成練習片段 / 測資，但不得偽裝成正式 OJ 題。

9. **EEG / webcam / attention / emotion detection**
   - 不使用腦波、鏡頭、情緒辨識等高成本低證據價值系統。

10. **Review debt**
    - deferred review 不變成欠作業。

11. **工程功能數 KPI**
    - 完成多少 subsystem 不等於版本成功。

---

# 8｜題目智慧生命週期

題目智慧只處理「如何理解與使用題目」，不創造第二份 Problem identity。

## 8.1 L0｜已索引

最小資料：

- source；
- external problem ID；
- title；
- canonical URL；
- basic statement metadata；
- constraints（若可靠取得）；
- dedupe identity。

用途：

- 題庫搜尋；
- 後續分類。

成本要低，可批次大量建立。

## 8.2 L1｜已分類

增加 AI candidate：

- Primary Skill candidate；
- supporting Skill candidate；
- difficulty candidate；
- prerequisite candidate；
- expected complexity；
- Activity / Role candidate；
- alternate solution risk；
- evidence suitability candidate。

原則：

- AI 新分類預設是 Candidate；
- 高 confidence + deterministic rule 可自動進 staging；
- ambiguity 高時進 Needs QA；
- 不要求 learner 手動補 metadata。

## 8.3 L2｜教學就緒

只針對高價值題。

增加：

- 問題模型；
- 關鍵觀察；
- correctness reasoning；
- invariant；
- complexity；
- common pitfalls；
- edge cases；
- A1–A5 hints；
- reference solution；
- alternate approaches；
- generated tests；
- transfer signals。

L2 不代表一定 Published。

## 8.4 驗證層級

AI 產出的 solution / test 不得直接標「正確」。

建議 trust states：

```text
AI Candidate
→ Compile Verified
→ Sample Verified
→ Differential Verified
→ OJ Accepted
```

其中：

- Compile Verified：只代表可編譯；
- Sample Verified：只代表 sample；
- Differential Verified：代表與可信 oracle / brute force 對大量小測資一致；
- OJ Accepted：才代表外部 Judge AC。

## 8.5 Runtime eligibility 與內容品質分離

題目可：

- Indexed；
- Classified；
- Teaching-ready；

但仍不一定進 Published Curriculum。

正式 placement 仍依現有 curriculum publish contract。

## 8.6 Deep enrichment 觸發條件

不得對所有 Indexed 題生成完整教材。

只有以下情境才進 L2：

- Today 即將使用；
- Lesson 缺 teaching-ready 題；
- Transfer pool coverage 不足；
- Exam pool 需要；
- learner 主動要求；
- curation 判定高價值。

---

# 9｜外部 OJ 與自建平台的分工

```text
外部 OJ
= 題目來源 + verdict authority

APCS Learning System
= 分類 + 教學 + route + Evidence + repair + transfer
```

可以自建：

- local sample runner；
- generated boundary tests；
- differential tests。

但不能把 local test PASS 說成 OJ AC。

---

# 10｜Problem Library 設計

Learner-facing 頁面最多提供必要篩選：

- 未做；
- 做過；
- Repair；
- Transfer；
- Mock；
- Skill；
- Unit；
- Source；
- Difficulty。

進階查詢優先由自然語言完成，不做 30 個 filter。

例如：

> 找一題我沒做過、約 15 分鐘、偏 5+5、不要提示方法。

ChatGPT 讀取 Problem Intelligence 後選題。

推薦必須可解釋：

```text
為什麼推薦：
- 未做過
- 與目前 route 相符
- transfer distance 合理
- 預估 15–20 分鐘
- 不和最近題目過度重複
```

---

# 11｜Spoiler Boundary

任何 learner-facing 題目資料必須分成：

## Pre-attempt

可安全顯示：

- 題面；
- I/O；
- constraints；
- time budget；
- 必要背景（依 Activity）。

## Post-attempt

才可解鎖：

- Primary Skill；
- key observation；
- solution；
- hints；
- pitfalls；
- alternate method；
- transfer signals。

正式 Transfer / Mock 的 internal classification 必須對 learner 隱藏。

---

# 12｜Learner Model v2

v2.4 不建立一個新的「學習者總分」。

Learner Model 由多個可解釋訊號組成：

```text
Retention
Transfer
Hint dependence
Bottleneck recurrence
Metacognition
Exam execution
```

其中 durable truth 仍是 Attempt / Evidence。

其他狀態：

- derived；
- 可重建；
- versioned；
- 不得手動宣告 mastery。

---

# 13｜Memory Policy v0.2 原則

目前 v0.1 參數是保守先驗，不直接視為個人最佳值。

v2.4 先建立 calibration：

```text
預測 R
vs
真實 delayed retrieval outcome
```

再比較候選 policy：

- calibration error；
- review load；
- missed failures；
- new-learning capacity；
- transfer outcome。

資料不足：

**不調參。**

---

# 14｜跨日鞏固原則

不用 sleep tracking。

只區分：

- same-session；
- same-day；
- cross-day；
- multi-day。

同日反覆成功不得被當成強長期 retention evidence。

重要 Skill 應優先出現：

```text
初學
→ 短 retrieval
→ 跨日 retest
→ delayed transfer
```

---

# 15｜Today v2 的 learner experience

理想畫面：

```text
今日學習｜約 60 分鐘

1. 8 min
   Prefix Sum Reading retrieval

2. 22 min
   新學習

3. 15 min
   方法辨識

4. 12 min
   Transfer

[開始]
```

每個 activity 可有：

```text
Why?
```

用來解釋：

- 為什麼現在；
- 依據什麼 Evidence；
- 是否因 recent fail；
- 是否因 retention risk；
- 是否為 transfer / exam preparation。

但 learner 不需要先管理 scheduler。

---

# 16｜版本成功指標

v2.4 不以：

- 題目總數；
- Lesson 數；
- dashboard 數；
- AI output 數；

為成功標準。

主要觀察：

| 指標 | 方向 |
| --- | --- |
| A0 Transfer PASS rate | ↑ |
| delayed cold retrieval | ↑ |
| same-problem-repeat dependence | ↓ |
| hint dependence | ↓ |
| strategy-selection error | ↓ |
| repeated root cause | ↓ |
| debugging localization time | ↓ |
| time-to-correct implementation | ↓ |
| exam sunk-time loss | ↓ |
| memory prediction calibration | ↑ |
| confidence calibration | ↑ |
| management overhead | ↓ / 保持低 |
| new-learning capacity | 必須保護 |

---

# 17｜三個 learner-facing 主入口上限

v2.4 原則上最多保留三個主要入口：

```text
Today
Problem Library
Exam
```

其他：

- Evidence；
- Memory；
- Calibration；
- Repair；
- Enrichment；
- AI classification；

全部盡量在背後運作。

如未來真的需要新增第四個入口，必須證明前三個無法合理承載。

---

# 18｜Gate C0–C10

## C0｜Authority 與文件收斂

目標：

- 建立本 v2.4 contract；
- 修正 v2.3 文件中過期的 CURRENT / Draft 描述；
- current authority 只從單一 machine-readable source 投影；
- 歷史 release 清楚標示 historical。

完成條件：

- 不改 learner behavior；
- production authority 無歧義；
- README / architecture / Notion current callout 不互相矛盾。

---

## C1｜題目智慧 MVP

MVP = Minimum Viable Product，中文即「最小可用版本」。

目標：

- URL 單題 import；
- batch import；
- ZeroJudge first；
- dedupe；
- L0 indexing；
- L1 classification；
- confidence / Needs QA；
- 不要求 learner 填 metadata。

完成條件：

- 一批外部題可以低成本 index；
- AI classification 不直接進 Published；
- ambiguous row fail-closed；
- Problem identity 不建立第二份 SSOT。

---

## C2｜Deep Enrichment 與驗證

目標：

- L2 teaching package；
- A1–A5 hints；
- solution candidate；
- complexity；
- edge cases；
- generated tests；
- compile/sample/differential validation。

完成條件：

- AI Candidate 與 OJ Accepted 不混淆；
- sample PASS 不宣稱 correctness；
- enrichment 可重建 / versioned；
- 沒有 learner form 增長。

---

## C3｜Problem Library + Spoiler Firewall

目標：

- learner search；
- natural-language retrieval；
- pre/post attempt visibility；
- Transfer / Mock classification hiding。

完成條件：

- learner 能快速找題；
- Transfer 不洩漏方法；
- learner-facing filters 保持精簡。

---

## C4｜認知編排器

目標：

- strategy discrimination；
- interleaving；
- guidance fading；
- closed-loop repair；
- Today v2。

完成條件：

- Today 可選 Review / New / Repair / Discrimination / Transfer；
- 每日仍受 capacity governor；
- 新學習時間不被吃光；
- deferred 不算 debt；
- task recommendation 可解釋。

---

## C5｜Learner Model v2

目標：

- hint dependence；
- transfer state；
- repeated bottleneck；
- optional confidence sampling；
- misconception candidate logic。

完成條件：

- 不新增黑箱 mastery；
- confidence 不進 Gate；
- 單次 typo 不升級成永久弱點；
- learner-facing 操作符合 friction budget。

---

## C6｜Exam Runtime

目標：

- timed mixed practice；
- scan / select / stop-loss；
- compile / submit / switch timestamps；
- minimal postmortem。

完成條件：

- 大部分資料自動取得；
- 能區分「不會 / 想太久 / 寫太慢 / bug / 看錯 / complexity / 時間配置」；
- 不把所有失分歸為粗心。

---

## C7｜Calibration Infrastructure

目標：

- predicted retrievability vs actual outcome；
- offline replay；
- candidate policy comparison；
- feature flag rollout。

完成條件：

- 不做 online ML；
- 資料不足不調參；
- policy change 可完整 rebuild；
- v0.1 仍可 rollback。

---

## C8｜Genuine Learner Pilot

這是第一個必須有真實 learner activity 的 Gate。

目標：

- Today v2 真實使用；
- Problem Intelligence 真實選題；
- Repair / Transfer 真實使用；
- Exam mini-session 真實使用；
- friction 實測。

完成條件：

- 不能用工程 test 取代；
- 必須有真實 A0 / delayed / transfer evidence；
- 收集「哪裡操作麻煩」而不是只看功能 PASS。

---

## C9｜Policy Calibration

只有 C8 產生足夠真實 Evidence 才開始。

目標：

- memory candidate policy；
- guidance threshold；
- discrimination scheduling；
- repair recurrence policy；
- Today capacity tuning。

完成條件：

- offline comparison 優於 current policy；
- 不增加 learner friction；
- review load 不失控；
- rollout 可 rollback。

---

## C10｜Readiness / v2.4 Closure

目標：

- final production QA；
- learner UX acceptance；
- delayed / transfer / timed evidence；
- RR3 / IR3 或當時適用的 readiness gate administration。

重要：

```text
v2.4 engineering complete
≠
learner readiness PASS
```

若 learner evidence 不足：

```text
LEARNER_READINESS = NOT ASSESSED
```

仍是合法 closure。

---

# 19｜Gate 執行順序

正式順序：

```text
C0
→ C1
→ C2
→ C3
→ C4
→ C5
→ C6
→ C7
→ C8
→ C9
→ C10
```

但允許 C1–C3 的非 learner-facing backend work 部分平行。

不得：

- C8 前製造假 learner Evidence；
- C9 前用少量假資料「優化」scheduler；
- C10 前因工程完成宣稱 readiness。

---

# 20｜Anti-overengineering Stop Rule

任何 feature 在實作前與 review 時都問：

1. 是否減少 learner 操作？
2. 是否改善 task selection？
3. 是否改善 Evidence 品質？
4. 是否改善 transfer / debugging / exam performance？
5. 是否減少重複人工管理？

如果五項都沒有明確改善：

**停止實作。**

同時，任何 subsystem 若需要 learner 每天手動維護，預設視為設計失敗，除非這個輸入本身就是學習活動。

---

# 21｜v2.4 Core / Optional / Non-goals 最終固定版

## Core

- 題目智慧 L0 / L1 / L2；
- batch import；
- Problem Library；
- natural-language problem search；
- spoiler firewall；
- hint ladder；
- strategy discrimination；
- interleaving；
- guidance fading；
- closed-loop repair；
- Today v2；
- Learner Model v2 的必要訊號；
- Exam Runtime；
- calibration infrastructure；
- learner friction budget enforcement。

## Optional

- confidence sampling；
- mental effort sampling；
- misconception candidate；
- advanced personalization；
- Learning Status v2 advanced analytics。

## Non-goals

- universal OJ；
- hidden mastery score；
- AI-awarded readiness；
- large learner forms；
- duplicated curriculum；
- duplicated adaptive memory；
- Reading parallel curriculum；
- AI-generated official-style problem farm；
- EEG / webcam attention systems；
- review debt；
- feature-count-driven development。

---

# 22｜版本完成定義

v2.4 完成不是：

> 「我們做完 C0–C10 所有程式。」

而是：

> **系統能在極低 learner friction 下，從可靠題目庫與真實 Evidence 中，安排更好的學習活動，逐步減少提示，修復真正 bottleneck，驗證 transfer，並支援正式考試執行；同時不製造虛假的 mastery/readiness。**

---

# 23｜與 v2.3 的相容承諾

在 v2.4 未完成並通過對應 Gate 前：

- v2.3 production authority 保持有效；
- Worker #58 production 不因本規劃自動改變；
- 既有 REC / EV schema 不因「可能有用」而新增欄位；
- 既有 52 Lesson / 14 Unit curriculum 不自動擴張；
- #32 genuine learner validation 仍保留；
- #40 staging curation 仍 fail-closed；
- `LEARNER_READINESS = NOT ASSESSED`。

---

# 24｜最終產品準則

v2.4 所有設計最後都用一句話判斷：

> **如果這個功能不能讓學習者更快進入真正的思考、解題、實作、除錯或 transfer，就不應該讓學習者看到它。**

