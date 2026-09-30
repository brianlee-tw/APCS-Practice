#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    bool first_case = true; 

    for (int i = 0; i < n; i++) {
        int a, f;
        cin >> a >> f;

        if (!first_case) {
            cout << '\n'; 
        }
        first_case = false;

        for (int j = 0; j < f; j++) {
            if (j > 0) {
                cout << '\n'; 
            }

            for (int k = 1; k <= a; k++) {
                cout << string(k, '0' + k) << '\n';
            }
            
            for (int k = (a - 1); k >= 1; k--) {
                cout << string(k, '0' + k) << '\n';
            }
        }
    }

    return 0;
}