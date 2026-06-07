# APCS Title: c005. 10300 - Ecological Premium
# APCS Complexity: O(N)
# APCS Tag: Math Theory, Basic Syntax, I/O Optimization
# APCS Difficulty: 2
# APCS Note: https://app.notion.com/p/c005-Ecological-Premium-Optimized-36a43be958cd80b99d7aff62c77cffe0?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

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