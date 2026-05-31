<br>

# 06_Math_Theory: 數學與數論演算法

本節探討常見的數學關係、數論特性，以及如何引入高效容器來處理動態數學問題。

<br>

---

<br>


## 📌 學習目標 (Objectives)
- **基礎鞏固**：掌握輾轉相除法（求 GCD）與 $O(\sqrt{N})$ 質數判定等基礎數論。
- **效率優化**：理解高效關聯容器（如 Map/Set/Priority Queue）對數學統計的優化。
- **邊界案例**：防範數值計算過程中的整數溢位（溢出時須全面改用 `long long`）。

<br>

---

## 📝 題目索引 (Problem Index)

<!-- L2_START -->
| 題目名稱 | 程式連結 | 時間複雜度 | 詳細筆記 | 難度 | 核心觀念 | 狀態 |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **a010. 因數分解** | [C++](./a010_prime_factor.cpp) [Py](./a010_prime_factor.py) | $O(\sqrt{N})$ | [📝 Notion](https://www.notion.so/a010-36a43be958cd80d7a665d58550e2e017?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | ★ ★ ★ ☆ ☆ | `數學與數論` `重複迴圈` `質因數分解` | ✅ 已過關 |
| **a034. 二進位制轉換** | [C++](./a034_Binary_Conversion_String.cpp) [Py](./a034_Binary_Conversion_String.py) | $O(\log  N)$ | [📝 Notion](https://www.notion.so/a034-36a43be958cd80a49057f8b8925ed00d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | ★ ★ ☆ ☆ ☆ | `基礎語法` `數學與數論` | ✅ 已過關 |
| **a059. 完全平方和** | [C++](./a059_Perfect_Squares_Sum.cpp) [Py](./a059_Perfect_Squares_Sum.py) | $O(\sqrt{b})$ | [📝 Notion](https://www.notion.so/a059-36a43be958cd800ca7f7e72ae7600618?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | ★ ☆ ☆ ☆ ☆ | `數學與數論` `基礎輸入輸出` | ✅ 已過關 |
| **a248. 除法練習** | [Py](./a248_division_pricision.py) | $O(N)$ | [📝 Notion](https://www.notion.so/a248-36a43be958cd80caa5c6cd956b53148a?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | ★ ★ ☆ ☆ ☆ | `Math_Theory` `IO_Optimization` | ✅ 已過關 |
| **a453. TOI2010 <br> 第一題：一元二次方程式** | [Py](./a453_QuadraticEquationRationalRoot.py) | $O(M)$ | [📝 Notion](https://www.notion.so/a453-TOI2010-36a43be958cd80ef8219fcaf13eec7d1?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | ★ ☆ ☆ ☆ ☆ | `Math_Theory` `Conditionals` | 🚧 進行中 |
<!-- L2_END -->

<br>

---

<br>

## 💡 解題筆記 (Key Notes)
- **核心重點**：數論演算法的核心是「利用數學規律降低計算複雜度」（例如從 $O(N)$ 降到 $O(\log N)$）。
- **常見陷阱**：高頻率將資料丟入陣列重新排序（`sort`）會大幅超時，應善用 `priority_queue` 自動維持極值。
- **進階思考**：許多看似複雜的模擬題目，只要推導出其背後的多項式或遞迴式，就能直接轉換為數學解。
