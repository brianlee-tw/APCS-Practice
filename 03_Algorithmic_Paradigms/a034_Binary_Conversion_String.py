import sys
while True:
    try:
        n = int(input())
        ans = bin(n)[2:]
        print(ans)
    except EOFError:
        break