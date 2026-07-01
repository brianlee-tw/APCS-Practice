// APCS Title: a148. You Cannot Pass?!
// APCS Complexity: O(N)
// APCS Tag: Conditionals, Loops, Math Theory
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/a148-You-Cannot-Pass-39043be958cd808999dfdceb9a51a348?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

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