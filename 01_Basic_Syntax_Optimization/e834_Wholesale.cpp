// APCS Title: e834. 批發量
// APCS Complexity: O(N)
// APCS Tag: IO Optimization, Conditionals, Loops
// APCS Difficulty: 1
// APCS Note: 

#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);

    int m, t;
    if (cin >> m) { // 先讀入每箱基準量
        while (cin >> t) {
            if (t == 0) {
                break; // 偵測到 0 結束
            }

            // 修正：應將原先的 10 全部改為變數 m
            if (t % m == 0) {
                cout << t / m << '\n';
            } else {
                cout << m - (t % m) << '\n';
            }
        }
    }
    return 0;
}