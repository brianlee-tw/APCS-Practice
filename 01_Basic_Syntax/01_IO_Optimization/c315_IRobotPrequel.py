# APCS Title: c315. 座標移動
# APCS Complexity: O(N)
# APCS Tag: 基礎輸入輸出, 條件判斷
# APCS Difficulty: 1
# APCS Note: https://www.notion.so/c315-I-ROBOT-36a43be958cd804ba58adaf8849c51cc?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

n=int(input())
x = 0
y = 0
for i in range(n):
    a, b = map(int,input().split())

    if a == 0 :
        y += b
    elif a == 1:
        x += b
    elif a == 2:
        y -= b
    elif a == 3:
        x -= b

print(x, y) 
