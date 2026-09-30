import sys
while True:
    try:
        a, b, n=map(int,input().split())
        ans = [str(a // b), "."]        # 整數部分
        r = a % b

        for _ in range(n):
            r *= 10
            ans.append(str(r // b))
            r %= b


        else:
            print("".join(ans))            
    
    except EOFError:
        break
