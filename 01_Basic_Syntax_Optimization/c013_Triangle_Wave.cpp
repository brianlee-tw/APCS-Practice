// APCS Title: c013. 00488 - Triangle Wave
// APCS Complexity: O(n * f * a^2)
// APCS Tag: Loops
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/c013-Triangle-Wave-39a43be958cd807d9f75daedeb06dc45?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-11

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