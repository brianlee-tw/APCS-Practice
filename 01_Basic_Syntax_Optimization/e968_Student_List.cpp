#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (cin >> n) {

        vector<int> a(n + 1, 0);

        // 固定讀入 3 個缺席學生的座號
        for (int i = 0; i < 3; i++){
            int m;
            cin >> m;
            a[m] = 1; // 1 代表缺席
        }

        for (int j = n; j > 0; j--){
            if (a[j] == 0){ // 0 代表出席
                cout << "No. " << j << '\n';
            }
        }
    }

    return 0;
}