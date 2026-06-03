# APCS Title: a453. TOI2010 <br> 第一題：一元二次方程式
# APCS Complexity: O(m)
# APCS Tag: Math Theory, Conditionals
# APCS Difficulty: 1
# APCS Note: https://www.notion.so/a453-TOI2010-36a43be958cd80ef8219fcaf13eec7d1?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import math

n = int(input())
for _ in range(n):

    a, b, c = map(int, input().split())

    if (b * b - 4 * a * c) >= 0:
        if math.isqrt(b * b - 4 * a * c) **2 == (b * b - 4 * a * c) :
                   
            print("Yes")

        else:
                    
            print("No")

    else:
                
        print("No")

  

