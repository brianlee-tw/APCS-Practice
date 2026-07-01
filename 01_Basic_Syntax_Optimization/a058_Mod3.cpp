// APCS Title: a058. MOD3
// APCS Complexity: O(N)
// APCS Tag: IO Optimization, Loops, Array
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/a058-MOD3-39043be958cd80768d9fdf5c05b9ed54?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);

    int n;
    if (cin >> n) {
        // 使用陣列代替獨立變數：counts[0]存餘0, counts[1]存餘1, counts[2]存餘2
        int counts[3] = {0}; 

        for (int i = 0; i < n; i++) {
            int m;
            cin >> m;
            // 關鍵優化：直接用餘數當作陣列索引
            counts[m % 3]++;
        }

        cout << counts[0] << ' ' << counts[1] << ' ' << counts[2] << '\n';
    }
    return 0;
}