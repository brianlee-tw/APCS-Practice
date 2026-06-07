# APCS Title: c079. 10346 - Peter's Smokes
# APCS Complexity: O(1)
# APCS Tag: Math Theory, I/O Optimization
# APCS Difficulty: 2
# APCS Note: https://app.notion.com/p/c079-Peter-s-Smokes-36a43be958cd8066b805e54b3fed1e0b?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

import sys

def main():
    # 批次讀入並利用 map 一口氣將所有元素轉成整數
    input_data = list(map(int, sys.stdin.read().split()))
    if not input_data:
        return
    
    iterator = iter(input_data)
    
    while True:
        try:
            n = next(iterator)
            k = next(iterator)
            
            # O(1) 數學核心公式
            # (n - 1) 為扣除最後一根必定無法再兌換的後，能拿去兌換的
            # (k - 1) 為成功多換一根菸所需要付出的「淨消耗屁股數」
            total = n + (n - 1) // (k - 1)
            
            print(total)
            
        except StopIteration:
            break

if __name__ == "__main__":
    main()