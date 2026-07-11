// APCS Title: e927. Matrix Symmetry
// APCS Complexity: O(N*M)
// APCS Tag: Conditionals, Loops, Array, Vector
// APCS Difficulty: 2
// APCS Note: https://app.notion.com/p/b367-39a43be958cd80d0a5c7e033b8079c5f?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-11

#include <bits/stdc++.h>

using namespace std;

void solve() {
    int n, m;
    cin >> n >> m;
    bool is_reverse = true;

    vector<vector<int>> v(n, vector<int>(m, 0));

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            cin >> v[i][j];
        }
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (v[i][j] != v[n - i - 1][m - j - 1]) {
                is_reverse = false;
                break; 
            }
        }
        if (!is_reverse) break; 
    }

    if (is_reverse) {
        cout << "go forward\n";
    } else {
        cout << "keep defending\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }

    return 0;
}