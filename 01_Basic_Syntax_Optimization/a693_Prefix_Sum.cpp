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