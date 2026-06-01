# APCS Title: a695. 找出最大質因數
# APCS Complexity: O(sqrt(N))
# APCS Tag: Math_Theory, Loops
# APCS Difficulty: 2
# APCS Note: https://www.notion.so/a695-NOIP-2012-1-36a43be958cd80b6909dce9a7c837921?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import math

n = int(input())

if n % 2 == 0:      #先判斷質因數是否有 2
    print(n // 2)
else:
    for i in range(3, math.isqrt(n) + 1, 2):
        if n % i == 0:      # 找到較小質因數 i
            print(n // i)   # 輸出較大質因數 n // i
            break           # 題目確定只有兩個質因數, 跳出迴圈