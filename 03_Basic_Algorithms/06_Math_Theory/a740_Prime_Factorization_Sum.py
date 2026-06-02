import math

while True:
    try:
        n = int(input())
        cnt = 0

        if n % 2 == 0:
            while n % 2 == 0:
                cnt += 2
                n //= 2

        for i in range(3, math.isqrt(n) + 1, 2):
            while n % i == 0:
                cnt += i
                n //= i

        if n != 1:
            cnt += n

        print(cnt)


    except EOFError:
        break