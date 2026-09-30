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