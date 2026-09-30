import math

n = int(input())

if n % 2 == 0:      #先判斷質因數是否有 2
    print(n // 2)
else:
    for i in range(3, math.isqrt(n) + 1, 2):
        if n % i == 0:      # 找到較小質因數 i
            print(n // i)   # 輸出較大質因數 n // i
            break           # 題目確定只有兩個質因數, 跳出迴圈