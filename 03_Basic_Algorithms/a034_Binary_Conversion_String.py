# APCS Title: a034. 二進位制轉換
# APCS Complexity: O(\log n)
# APCS Tag: Basic Syntax, Loops, Math Theory
# APCS Difficulty: 2
# APCS Note: https://www.notion.so/a034-36a43be958cd80a49057f8b8925ed00d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import sys
while True:
    try:
        n = int(input())
        ans = bin(n)[2:]
        print(ans)
    except EOFError:
        break