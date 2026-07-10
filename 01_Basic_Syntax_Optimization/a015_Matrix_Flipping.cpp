// APCS Title: a015. 矩陣的翻轉
// APCS Complexity: O(R * C)
// APCS Tag: IO Optimization, Array
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/a015-39943be958cd80058d9df0f6fdab49b9?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>

using namespace std;

int a[105][105];

int main() {

    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int r, c;
    while (cin >> r >> c) {

        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) {
                cin >> a[i][j];
            }
        }

        for (int k = 0; k < c; k++) {
            for (int l = 0; l < r; l++) {
                cout << a[l][k] << " ";
            }
            cout << '\n';
        }
    }
    return 0;
}