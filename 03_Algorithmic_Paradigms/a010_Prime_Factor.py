import sys


def main():
    # 讀取系統標準輸入
    line = sys.stdin.readline()
    if not line:
        return
    n = int(line.strip())

    first = True

    # 1. 先單獨處理唯一的偶質數 2，優化後續奇數步長
    if n % 2 == 0:
        cnt = 0
        while n % 2 == 0:
            n //= 2
            cnt += 1

        print("2", end="")
        if cnt > 1:
            print("^" + str(cnt), end="")
        first = False

    # 2. 從 3 開始只走奇數步長，範圍限制在根號內
    i = 3
    while i * i <= n:
        if n % i == 0:
            cnt = 0
            while n % i == 0:
                n //= i
                cnt += 1

            # 處理乘號的輸出時機
            if not first:
                print(" * ", end="")

            print(i, end="")
            if cnt > 1:
                print("^" + str(cnt), end="")
            first = False
        i += 2

    # 3. 處理最後殘留大於根號的大質數
    if n > 1:
        if not first:
            print(" * ", end="")
        print(n, end="")
    print()


if __name__ == "__main__":
    main()
