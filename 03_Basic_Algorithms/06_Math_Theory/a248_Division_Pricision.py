# APCS Title: a248. 除法練習
# APCS Complexity: O(n)
# APCS Tag: Math Theory, I/O Optimization
# APCS Difficulty: 2
# APCS Note: https://www.notion.so/a248-36a43be958cd80caa5c6cd956b53148a?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

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
