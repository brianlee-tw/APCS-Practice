// APCS Title: d669. Alarm Clock
// APCS Complexity: O(1)
// APCS Tag: IO Optimization, Conditionals, Math Theory
// APCS Difficulty: 1
// APCS Note: 

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