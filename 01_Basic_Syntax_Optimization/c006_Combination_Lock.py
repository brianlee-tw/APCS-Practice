# APCS Title: c006. 10550 - Combination Lock
# APCS Complexity: O(1) per testcase
# APCS Tag: Math Theory, Basic Syntax, I/O Optimization
# APCS Difficulty: 2
# APCS Note: https://app.notion.com/p/c006-Combination-Lock-36a43be958cd80a883afd8dc560bcb76?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import sys

def main():
    # 批次讀入所有測資並直接轉換為整數列表
    input_data = list(map(int, sys.stdin.read().split()))
    if not input_data:
        return
    
    # 建立整數型態的迭代器
    iterator = iter(input_data)

    while True:
        try:
            s  = next(iterator)
            p1 = next(iterator)
            p2 = next(iterator)
            p3 = next(iterator)
            
            # 終止條件：四個數字皆為 0
            if s == p1 == p2 == p3 == 0:
                break

            # 總共轉 3 圈的固定度數 = 1080 度
            # 順時針 (刻度變小): (A - B + 40) % 40
            # 逆時針 (刻度變大): (B - A + 40) % 40
            ticks = 0
            ticks += (s - p1 + 40) % 40   # 第一段：順時鐘從 s 到 p1
            ticks += (p2 - p1 + 40) % 40  # 第二段：逆時鐘從 p1 到 p2
            ticks += (p2 - p3 + 40) % 40  # 第三段：順時鐘從 p2 到 p3

            # 總角度 = 總格數 * 9 度 + 基礎 1080 度
            print(ticks * 9 + 1080)

        except StopIteration:
            break

if __name__ == "__main__":
    main()