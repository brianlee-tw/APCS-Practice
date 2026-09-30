#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int z, i, m, l, cnt = 0;

    while(cin >> z >> i >> m >> l){

        if (z == 0 && i == 0 && m == 0 && l == 0){
            break;
        }

        cnt++;
        int t = 1, a[10005] = {0};
        a[l] = 1; 

        while (true){

            t++; 

            int random = (z * l + i) % m;
            l = random;
            
            if (a[random] == 0){
                a[random] = t;
            }
            else{
                // 直接相減即為正確週期
                cout << "Case " << cnt << ": " << (t - a[random]) << '\n';
                break;
            }
        }
    }

    return 0;
}