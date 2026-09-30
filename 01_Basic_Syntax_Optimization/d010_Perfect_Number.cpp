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