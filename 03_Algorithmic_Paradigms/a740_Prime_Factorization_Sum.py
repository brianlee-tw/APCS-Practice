# APCS Title: a740. 質因數之和
# APCS Complexity: O(\sqrt{n})
# APCS Tag: Math Theory, I/O Optimization
# APCS Difficulty: 2
# APCS Note: https://www.notion.so/a740-36a43be958cd80c1af62cde1c3eb1e24?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import sys

def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    results = []
    for s in input_data:
        n = int(s)
        cnt = 0

        while n % 2 == 0:
            cnt += 2
            n //= 2

        i = 3                     # 處理 3 開始的奇數
        while i * i <= n:         # 使用 while 條件動態判斷，隨 n 變小而縮減運算範圍
            while n % i == 0:
                cnt += i
                n //= i
            i += 2

        if n > 1:                 # 若剩餘的 n > 1，則該數為質數
            cnt += n

        results.append(str(cnt))

    sys.stdout.write("\n".join(results) + "\n")

if __name__ == '__main__':
    main()