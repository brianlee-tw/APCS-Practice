#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

using ll = long long;

int main() {
    // 提升 I/O 執行效率
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;
    for (int i = 1; i <= n; ++i) {
        ll a, b;
        cin >> a >> b;
        ll cnt = 0;
        
        // 鎖定起始平方根，考慮 a 是否為平方數
        ll start = ceil(sqrt(a));

        for (ll j = start; j * j <= b; ++j) {
            cnt += j * j;
        }

        cout << "Case " << i << ": " << cnt << "\n";
    }

    return 0;
}