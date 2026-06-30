# APCS Title: c276. 沒有手機的下課時間
# APCS Complexity: O(n)
# APCS Tag: Basic Syntax, Loops, Conditionals
# APCS Difficulty: 2
# APCS Note: https://app.notion.com/p/c276-36a43be958cd80c8a553deb0e047aecf?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import sys

def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    iterator = iter(input_data)

    while True:
        try:
            # 修正：直接以字串處理，移除不必要的 int() 轉換
            correct = next(iterator)
            n = int(next(iterator))
            
            for _ in range(n):
                A_count = 0
                B_count = 0
                digits = next(iterator)

                for c, d in zip(correct, digits):
                    if d == c:
                        A_count += 1
                    elif d in correct:
                        B_count += 1

                print(f"{A_count}A{B_count}B")

        except StopIteration:
            break

if __name__ == "__main__":
    main()