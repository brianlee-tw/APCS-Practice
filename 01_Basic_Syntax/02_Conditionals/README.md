<br>

# 02_Conditionals: 邏輯判斷

本節重點在於探討該主題的核心邏輯與常見解題策略，透過實作累積對語法與演算法的敏銳度。

<br>

---

<br>

##  學習目標 (Objectives)
- **基礎鞏固**：熟練 `if-else`、`switch-case` 以及三元運算子的靈活運用。
- **效率優化**：透過邏輯運算簡化巢狀判斷 (Nested If)，提高程式可讀性。
- **邊界案例**：掌握多重條件下的邊界數值判斷。

<br>

---

<br>

##  題目索引 (Problem Index)
<!-- L2_START -->
> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。

| 題目名稱 | 程式連結 | 時間複雜度 | 難度 | 核心觀念 | 狀態 |
| :--- | :---: | :--- | :--- | :--- | :---: |
| [**a244. for + if**](https://www.notion.so/a244-for-if-36a43be958cd8081aa57f6377251a74d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./a244_For_If_Practice.cpp) | $O(1)$ | ★ ☆ ☆ ☆ ☆ | `Basic Syntax`<br>`Conditionals` | ✅ Accepted |
| [**a244. for + if**](https://www.notion.so/a244-for-if-36a43be958cd8081aa57f6377251a74d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [Py](./a244_for_if_practice.py) | $O(1)$ | ★ ☆ ☆ ☆ ☆ | `Basic Syntax`<br>`Conditionals` | ✅ Accepted |
<!-- L2_END -->

<br>

---

<br>

##  解題筆記 (Key Notes)
- **核心重點**：透過邏輯運算符的「短路特性 (Short-circuit evaluation)」優化判斷速度；`switch` 在處理多個離散狀態時比 `if-else` 更清晰。
- **常見陷阱**：浮點數 (double/float) 比較時直接使用 `==`，應考慮使用一個極小的誤差值 $\epsilon$ (例如 `abs(a - b) < 1e-9`)。
- **進階思考**：在條件判斷極多時，是否可以透過「查表法 (Lookup Table)」將時間複雜度降至 $O(1)$。

<br>

---

<br>

*Back to [上一層目錄](../README.md)*