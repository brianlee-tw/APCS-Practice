# APCS Title: a686. 蝸牛往上爬
# APCS Complexity: O(1)
# APCS Tag: 數學與數論, 條件判斷
# APCS Difficulty: 2
# APCS Note: https://www.notion.so/a686-36a43be958cd8027842ac5abc1629bdb?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

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

