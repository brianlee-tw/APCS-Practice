// APCS Title: e834. 批發量
// APCS Complexity: O(N)
// APCS Tag: IO Optimization, Conditionals, Loops
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/e834-Wholesale-39043be958cd8051a9d3c5f451870bc4?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);

    int m, t;
    if (cin >> m) { 
        while (cin >> t) {
            if (t == 0) {
                break;
            }

            if (t % m == 0) {
                cout << t / m << '\n';
            } else {
                cout << m - (t % m) << '\n';
            }
        }
    }
    return 0;
}