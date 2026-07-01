// APCS Title: d070. 格瑞哥里的煩惱 (0 尾版)
// APCS Complexity: O(1)
// APCS Tag: IO Optimization, Conditionals, Loops
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/d070-0-39043be958cd8076a5e4c79eb19f02a4?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link 

#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);

    int y;
    while (cin >> y) {
        if (y == 0) {
            break;
        }

        if (y % 400 == 0) {
            cout << "a leap year\n";
        } else if (y % 100 == 0) {
            cout << "a normal year\n";
        } else if (y % 4 == 0) {
            cout << "a leap year\n";
        } else {
            cout << "a normal year\n";
        }
    }
    return 0;
}