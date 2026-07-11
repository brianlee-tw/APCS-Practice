// APCS Title: c085. Pseudo Randoms
// APCS Complexity: O(M)
// APCS Tag: Math Theory, Array
// APCS Difficulty: 2
// APCS Note: https://app.notion.com/p/c085-Pseudo-Random-Numbers-39943be958cd801aa8cac43e4e0e74ae?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

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