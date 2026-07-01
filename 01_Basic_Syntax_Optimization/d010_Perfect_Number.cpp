// APCS Title: d010. 盈虧數
// APCS Complexity: O(\sqrt{n})
// APCS Tag: Math Theory, Conditionals, Loops
// APCS Difficulty: 2
// APCS Note: https://app.notion.com/p/d010-39043be958cd801080ddc3a8929d2497?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>

using namespace std;

int main() {

    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;

    while (cin >> n) {
        int total = 0;

        for (int i = 1; i * i <= n; i++) {
            if (n % i == 0) {
                total += i;
                if (i != n / i) {
                    total += n / i;
                }
            }
        }

        total -= n; // 扣除自身

        if (total == n) {
            cout << "完全數\n";
        } else if (total > n) {
            cout << "盈數\n";
        } else {
            cout << "虧數\n";
        }
    }

    return 0;
}