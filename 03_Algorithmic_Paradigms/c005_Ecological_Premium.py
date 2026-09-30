import sys

def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    iterator = iter(input_data)
    
    n = int(next(iterator))
    
    for _ in range(n):
        f = int(next(iterator))
        total_bonus = 0
        
        for _ in range(f):
            farm_size = int(next(iterator))  # 面積
            _ = next(iterator)               # 動物數量（公式約分後無須使用，直接跳過）
            env_level = int(next(iterator))  # 環保等級
            
            # 累加該農夫獎金
            total_bonus += farm_size * env_level
        
        # 5. 印出該組總獎金
        print(total_bonus)

if __name__ == "__main__":
    main()