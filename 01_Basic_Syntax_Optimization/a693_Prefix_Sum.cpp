// APCS Title: a693. 吞食天地
// APCS Complexity: O(N + M)
// APCS Tag: Vector, Loops
// APCS Difficulty: 2
// APCS Note: https://app.notion.com/p/a693-3ab43be958cd80a0bb42fc5ccc621690?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-28

#include <iostream>
#include <vector>

using namespace std;

int main()
{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    while (cin >> n >> m)
    {
        // b[i] 表示前 i 個元素的累加和，長度需要 n + 1
        vector<long long> b(n + 1, 0);

        for (int i = 0; i < n; i++)
        {
            long long x;
            cin >> x;
            b[i + 1] = b[i] + x;
        }

        for (int i = 0; i < m; i++)
        {
            int l, r;
            cin >> l >> r;
            cout << (b[r] - b[l - 1]) << '\n';
        }
    }

    return 0;
}