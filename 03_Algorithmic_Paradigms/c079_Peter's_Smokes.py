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