#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main()
{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int r, c, m;

    while (cin >> r >> c >> m)
    {
        int arr[10][10], tmp[10][10];
        vector<int> op(m);

        for (int i = 0; i < r; i++)
        {
            for (int j = 0; j < c; j++)
            {
                cin >> arr[i][j];
            }
        }

        for (int i = 0; i < m; i++)
        {
            cin >> op[i];
        }

        // 倒序執行還原
        for (int i = m - 1; i >= 0; i--)
        {
            if (op[i] == 0)
            {
                for (int k = 0; k < r; k++)
                {
                    for (int j = 0; j < c; j++)
                    {
                        tmp[c - 1 - j][k] = arr[k][j];
                    }
                }
                swap(r, c);
            }
            else if (op[i] == 1)
            {
                for (int k = 0; k < r; k++)
                {
                    for (int j = 0; j < c; j++)
                    {
                        tmp[r - 1 - k][j] = arr[k][j];
                    }
                }
            }

            // 將暫存結果更新回原矩陣
            for (int k = 0; k < r; k++)
            {
                for (int j = 0; j < c; j++)
                {
                    arr[k][j] = tmp[k][j];
                }
            }
        }

        cout << r << " " << c << '\n';
        for (int i = 0; i < r; i++)
        {
            for (int j = 0; j < c; j++)
            {
                if (j > 0) cout << " ";
                cout << arr[i][j];
            }
            cout << '\n';
        }
    }

    return 0;
}