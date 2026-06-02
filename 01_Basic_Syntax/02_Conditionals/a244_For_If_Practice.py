# APCS Title: a244. for + if
# APCS Complexity: O(1)
# APCS Tag: Basic Syntax, Conditionals
# APCS Difficulty: 1
# APCS Note: https://www.notion.so/a244-for-if-36a43be958cd8081aa57f6377251a74d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

n = int(input())
for _ in range(n):
    a, b, c = map(int, input().split())
    if a == 1:
        print(b + c)
    elif a == 2:
        print(b - c)
    elif a == 3:
        print(b * c)
    elif a == 4:
        print(b // c)
