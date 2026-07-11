<br>

# 01_Basic_Syntax_Optimization: 語法特性與實作優化
本章節聚焦於 C++ 與 Python 的基礎語法高效應用，重點在於 I/O 優化與基礎邏輯的簡潔實現。

<br>

### 💡 學習策略
這些題目雖然基礎，但卻是所有高階算法的基石。重點在於觀察題目限制，並使用最適合的語法結構來降低時間複雜度。

<br>

### 關鍵術語
- `io`: 輸入輸出優化
- `cond`: 條件邏輯
- `loop`: 迴圈結構
- `func`: 函式封裝

<br>

<!-- L1_START -->
### 📊 當前章節複習進度：`33/50` (66%)

> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。

| 題目名稱 | 程式 | 複雜度 | 難度 | 核心觀念 | 狀態 | 最後編輯 |
| :--- | :---: | :--- | :--- | :--- | :---: | :---: |
| [**a001. 哈囉**](https://www.notion.so/a001-36a43be958cd80c48115f59d68f70a5f?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./a001_Hello_World.cpp) | $O(1)$ | ★ | `Basic Syntax` `IO Optimization` | ✅ | 2026-07-10 |
| [**a006. 一元二次方程式**](None) | [C++](./a006_One_Variable_Quadratic_Equation.cpp) | $O(1)$ | ★ | `Conditionals` `Math Theory` | 📝 | 2026-07-10 |
| [**a015. 矩陣的翻轉**](https://app.notion.com/p/a015-39943be958cd80058d9df0f6fdab49b9?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./a015_Matrix_Flipping.cpp) | $O(R * C)$ | ★ | `IO Optimization` `Array` | ✅ | 2026-07-10 |
| [**a038_Number_Reverse**](None) | [C++](./a038_Number_Reverse.cpp) | — | ★ |  | 📝 | 2026-07-10 |
| [**a058. MOD3**](https://app.notion.com/p/a058-MOD3-39043be958cd80768d9fdf5c05b9ed54?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./a058_Mod3.cpp) | $O(N)$ | ★ | `IO Optimization` `Loops` `Array` | ✅ | 2026-07-10 |
| [**a148. You Cannot Pass?!**](https://app.notion.com/p/a148-You-Cannot-Pass-39043be958cd808999dfdceb9a51a348?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./a148_You_Cannot_Pass.cpp) | $O(N)$ | ★ | `Conditionals` `Loops` `Math Theory` | ✅ | 2026-07-10 |
| [**a244. for + if**](https://www.notion.so/a244-for-if-36a43be958cd8081aa57f6377251a74d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [Py](./a244_For_If_Practice.py) [C++](./a244_For_If_Practice.cpp) | $O(1)$ | ★ | `Basic Syntax` `Conditionals` | ✅ | 2026-07-10 |
| [**a861. Secure Perimeter**](None) | [Py](./a861_Secure_The_Parimeter.py) | $O(n)$ | ★ | `Basic Syntax` `I/O Optimization` | 📝 | 2026-07-10 |
| [**c006. Combination Lock**](https://app.notion.com/p/c006-Combination-Lock-36a43be958cd80a883afd8dc560bcb76?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [Py](./c006_Combination_Lock.py) | $O(1)$ | ★★ | `Math Theory` `Basic Syntax` `I/O Optimization` | ✅ | 2026-07-10 |
| [**c022. Odd Sum**](https://app.notion.com/p/c022-Odd-Sum-39043be958cd8010b382cce73b1a44e3?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./c022_Odd_Sum.cpp) | $O(N)$ | ★ | `IO Optimization` `Loops` `Math Theory` | ✅ | 2026-07-10 |
| [**c085. 00350 - Pseudo-Random Numbers**](https://app.notion.com/p/c085-Pseudo-Random-Numbers-39943be958cd801aa8cac43e4e0e74ae?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./c085_Pseudo_Random_Numbers.cpp) | $O(M)$ | ★★ | `Math Theory` `Array` | ✅ | 2026-07-10 |
| [**c276. 沒有手機的下課時間**](https://app.notion.com/p/c276-36a43be958cd80c8a553deb0e047aecf?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [Py](./c276_Basic_Bulls_And_Cows.py) | $O(n)$ | ★★ | `Basic Syntax` `Loops` `Conditionals` | ✅ | 2026-07-10 |
| [**c315. 座標移動**](https://www.notion.so/c315-I-ROBOT-36a43be958cd804ba58adaf8849c51cc?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [Py](./c315_IRobotPrequel.py) | $O(n)$ | ★ | `Basic Syntax` `Conditionals` | ✅ | 2026-07-10 |
| [**c379. 成為出題者**](None) | [C++](./c379_Become_Quetion_Setter.cpp) | $O(1)$ | ★ | `IO Optimization` | 📝 | 2026-07-10 |
| [**d010. 盈虧數**](https://app.notion.com/p/d010-39043be958cd801080ddc3a8929d2497?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./d010_Perfect_Number.cpp) | $O(\sqrt{n})$ | ★★ | `Math Theory` `Conditionals` `Loops` | ✅ | 2026-07-10 |
| [**d049. 中華民國萬歲**](None) | [C++](./d049_Republic_of_China.cpp) | $O(1)$ | ★ | `IO Optimization` | 📝 | 2026-07-10 |
| [**d050. 妳那邊幾點**](None) | [C++](./d050_Time.cpp) | $O(1)$ | ★ | `IO Optimization` | 📝 | 2026-07-10 |
| [**d065. 三人行必有我師**](None) | [C++](./d065_Three_People_One_Teacher.cpp) | $O(1)$ | ★ | `Conditionals` | 📝 | 2026-07-10 |
| [**d066. 上學去吧！**](None) | [C++](./d066_Go_To_School.cpp) | $O(1)$ | ★ | `Conditionals` | 📝 | 2026-07-10 |
| [**d067. 格瑞哥里的煩惱 (1 行版)**](None) | [C++](./d067_Leap_Year.cpp) | $O(1)$ | ★ | `Conditionals` | 📝 | 2026-07-10 |
| [**d068. 該減肥了！**](None) | [C++](./d068_Loss_Weight.cpp) | $O(1)$ | ★ | `Conditionals` | 📝 | 2026-07-10 |
| [**d070. 格瑞哥里的煩惱 (0 尾版)**](https://app.notion.com/p/d070-0-39043be958cd8076a5e4c79eb19f02a4?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./d070_Leap_Year_0End.cpp) | $O(1)$ | ★ | `IO Optimization` `Conditionals` `Loops` | ✅ | 2026-07-10 |
| [**d071. 格瑞哥里的煩惱 (EOF 版)**](https://app.notion.com/p/d071-EOF-39043be958cd805aacd7e907233cf4c2?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./d071_Leap_Year_EOF.cpp) | $O(1)$ | ★ | `IO Optimization` `Conditionals` `Loops` | ✅ | 2026-07-10 |
| [**d072. 格瑞哥里的煩惱 (Case 版)**](https://app.notion.com/p/d071-EOF-39043be958cd805aacd7e907233cf4c2?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./d072_Leap_Year_Case.cpp) | $O(1)$ | ★ | `IO Optimization` `Conditionals` `Loops` | ✅ | 2026-07-10 |
| [**d073. 分組報告**](None) | [C++](./d073_Group_Project.cpp) | $O(1)$ | ★ | `IO Optimization` | 📝 | 2026-07-10 |
| [**d074. 電腦教室**](https://app.notion.com/p/d074-39043be958cd80b2b8cdea577aaaefaa?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./d074_Computer.cpp) | $O(N)$ | ★ | `IO Optimization` `Loops` | ✅ | 2026-07-10 |
| [**d097. 10038 - Jolly Jumpers**](https://app.notion.com/p/d097-Jolly-Jumpers-39943be958cd802d8552db3e93dae038?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./d097_Jolly_Jumpers.cpp) | $O(n)$ | ★★ | `Array` `String` `IO Optimization` | ✅ | 2026-07-10 |
| [**d669. Alarm Clock**](https://app.notion.com/p/d669-11677-Alarm-Clock-39043be958cd80769b6fc436b181a513?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./d669_Alarm_Clock.cpp) | $O(1)$ | ★ | `IO Optimization` `Conditionals` `Math Theory` | ✅ | 2026-07-10 |
| [**d827. 買鉛筆**](None) | [C++](./d827_Buy_Pencil.cpp) | $O(1)$ | ★ | `Math Theory` | 📝 | 2026-07-10 |
| [**e834. 批發量**](https://app.notion.com/p/e834-Wholesale-39043be958cd8051a9d3c5f451870bc4?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./e834_Wholesale.cpp) | $O(N)$ | ★ | `IO Optimization` `Conditionals` `Loops` | ✅ | 2026-07-10 |
| [**e835. 表演座位**](None) | [C++](./e835_Perform_Seat.cpp) | $O(1)$ | ★ | `Conditionals` `Math Theory` | 📝 | 2026-07-10 |
| [**e968. 2. 班級名單**](https://app.notion.com/p/e968-39043be958cd807c9ea0d79fff252e71?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./e968_Student_List.cpp) | $O(N)$ | ★ | `IO Optimization` `Loops` `Vector` | ✅ | 2026-07-10 |
| [**r488. apcs 彗星撞擊**](https://app.notion.com/p/r488-APCS-202510-M-1-39343be958cd803e8a1ac6fa7d8a4930?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link) | [C++](./r488_202510_M_Comet.cpp) | $O(R*C + K + M*S^2)$ | ★★★ | `Array` | ✅ | 2026-07-10 |
<!-- L1_END -->

<br>

*Back to [Main Repository](/README.md)*
