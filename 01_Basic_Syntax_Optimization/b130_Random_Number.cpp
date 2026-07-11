// APCS Title: b130. 明明的隨機數
// APCS Complexity: O(N log N)
// APCS Tag: IO Optimization, Sorting
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/b130-39a43be958cd8023afe5fca38b293ad5?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    while (cin >> n) {
        set<int> s;
        int num;

        for (int i = 0; i < n; i++) {
            cin >> num;
            s.insert(num);
        }

        cout << s.size() << '\n';

        bool is_first = true;
        for (int x : s) {
            if (!is_first) {
                cout << ' ';
            }
            cout << x;
            is_first = false;
        }
        cout << '\n';
    }

    return 0;
}