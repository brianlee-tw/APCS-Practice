// APCS Title: d074. 電腦教室
// APCS Complexity: O(N)
// APCS Tag: IO Optimization, Loops
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/d074-39043be958cd80b2b8cdea577aaaefaa?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

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