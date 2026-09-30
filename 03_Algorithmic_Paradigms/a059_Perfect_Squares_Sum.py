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

