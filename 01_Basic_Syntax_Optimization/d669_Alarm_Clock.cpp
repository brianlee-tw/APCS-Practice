// APCS Title: d669. Alarm Clock
// APCS Complexity: O(1)
// APCS Tag: IO Optimization, Conditionals, Math Theory
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/d669-11677-Alarm-Clock-39043be958cd80769b6fc436b181a513?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);

    int h1, m1, h2, m2;

    while (cin >> h1 >> m1 >> h2 >> m2) {

        if (h1 == 0 && m1 == 0 && h2 == 0 && m2 == 0) {
            break;
        }


        int t1 = h1 * 60 + m1;
        int t2 = h2 * 60 + m2;


        int t = ((t2 - t1) + 1440) % 1440;

        cout << t << '\n';
    }
}