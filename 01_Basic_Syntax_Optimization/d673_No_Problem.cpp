// APCS Title: d673. No Problem
// APCS Complexity: O(1)
// APCS Tag: IO Optimization, Loops, Array
// APCS Difficulty: 2
// APCS Note: https://app.notion.com/p/d673-No-Problem-39a43be958cd808c8228d90c85fb8035?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int s, cnt = 0;

    while (cin >> s) {
        if (s < 0) break;

        int a[12] = {0}, b[12] = {0}, remain = s;

        cnt++;
        cout << "Case " << cnt << ":\n";

        for (int i = 0; i < 12; i++) {
            cin >> a[i];
        }
        for (int i = 0; i < 12; i++) {
            cin >> b[i];
        }
        
        for (int i = 0; i < 12; i++) {
            if (remain < b[i]) {
                cout << "No problem. :(\n";
            } else {
                cout << "No problem! :D\n";
                remain -= b[i];
            }
            remain += a[i];
        }
    }
    return 0;
}