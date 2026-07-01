// APCS Title: d074. 電腦教室
// APCS Complexity: O(N)
// APCS Tag: IO Optimization, Loops
// APCS Difficulty: 1
// APCS Note: 

#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);

    int n;
    if (cin >> n) {
        int max_val = 0;
        for (int i = 0; i < n; i++) {
            int temp;
            cin >> temp;
            max_val = max(max_val, temp); 
        }
        cout << max_val << '\n';
    }
    return 0;
}