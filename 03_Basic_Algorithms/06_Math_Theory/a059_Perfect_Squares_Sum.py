# APCS Title: a059. 完全平方和
# APCS Complexity: O(sqrt(N))
# APCS Tag: Math Theory, Loops
# APCS Difficulty: 1
# APCS Note: https://www.notion.so/ZJ-A059-36a43be958cd800ca7f7e72ae7600618?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import math

n=int(input())
for i in range(1,n+1):
    a=int(input())
    b=int(input())
    cnt = 0

    start = math.isqrt(a)
    if start * start < a:  # a 是不是完全平方數
        start += 1
    
    curr = start
    while curr * curr <= b:
        cnt += (curr * curr)
        curr += 1
    
    print(f"Case {i}: {cnt}")

