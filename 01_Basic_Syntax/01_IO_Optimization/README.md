<br>

# 01_IO_Optimization: 輸入輸出優化

本節重點在於探討該主題的核心邏輯與常見解題策略，透過實作累積對語法與演算法的敏銳度。

<br>

---

<br>

##  學習目標 (Objectives)
- **基礎鞏固**：理解標準輸入輸出與緩衝區的運作機制。
- **效率優化**：掌握 `ios_base::sync_with_stdio(0); cin.tie(0);` 的使用時機，避免 I/O 成為效能瓶頸。
- **邊界案例**：熟練處理大量數據輸入與輸出格式的正確性。

<br>

---

<br>

##  題目索引 (Problem Index)
<!-- L2_START -->
> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。

| 題目名稱 | 程式連結 | 時間複雜度 | 難度 | 核心觀念 | 狀態 |
| :--- | :---: | :--- | :--- | :--- | :---: |
| [**a001. 哈囉**](https://www.notion.so/a001-36a43be958cd80c48115f59d68f70a5f?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./a001_Hello_World.cpp) | $O(1)$ | ★ ☆ ☆ ☆ ☆ | `Basic Syntax`<br>`IO Optimization` | ✅ Accepted |
| [**c315. 座標移動**](https://www.notion.so/c315-I-ROBOT-36a43be958cd804ba58adaf8849c51cc?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [Py](./c315_IRobotPrequel.py) | $O(n)$ | ★ ☆ ☆ ☆ ☆ | `Basic Syntax`<br>`Conditionals` | ✅ Accepted |
<!-- L2_END -->

<br>

---

<br>

##  解題筆記 (Key Notes)
- **核心重點**：`cin`/`cout` 在大量資料輸入時的效能瓶頸在於與 `stdio` 的同步以及緩衝區機制。
- **常見陷阱**：使用 `ios_base::sync_with_stdio(0); cin.tie(0);` 後，**絕對不能**混用 C 語言的 `scanf`/`printf`，否則會導致輸出順序錯亂或崩潰。
- **進階思考**：面對極端巨量資料時，考慮自行實作 `getchar_unlocked()` 進行字元層級的快速讀取。

<br>

---

<br>

*Back to [上一層目錄](../README.md)*
