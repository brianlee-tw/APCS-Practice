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

  

