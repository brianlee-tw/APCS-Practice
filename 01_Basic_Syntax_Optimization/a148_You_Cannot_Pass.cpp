#include <bits/stdc++.h>

using namespace std;

int main() {

    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;

    while (cin >> n) {
        int total = 0;

        for (int i = 0; i < n; i++) {
            cin >> m;
            total += m;
        }

        if (total > 59 * n) {
            cout << "no\n";  
        } else {
            cout << "yes\n"; 
        }
    }

    return 0;
}