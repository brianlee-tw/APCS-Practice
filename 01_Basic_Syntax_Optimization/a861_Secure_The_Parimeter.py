import sys
def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    for i in range(0, len(input_data), 2):
        h = int(input_data[i])
        w = int(input_data[i+1])
        print(2 * (w + h))

if __name__ == '__main__':
    main()