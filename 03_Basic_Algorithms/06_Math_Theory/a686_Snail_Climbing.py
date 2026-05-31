# APCS Title: a686. 蝸牛往上爬
# APCS Complexity: O(1)
# APCS Tag: 數學與數論, 條件判斷
# APCS Difficulty: 2
# APCS Note:

n = int(input())
for _ in range(n):
    x, y, z = map(int,input().split())
    if y >= x:
        print(1)
    elif y > z:
        ans = (x - z + (y - z) - 1) // (y - z)  # a // b 向下取整 ， (a + b - 1) // b 向上取整 (即商+1,但被除數-1,這樣原本整除就不會再多進位)
        print(ans)
    else:
        print("Poor Snail")

