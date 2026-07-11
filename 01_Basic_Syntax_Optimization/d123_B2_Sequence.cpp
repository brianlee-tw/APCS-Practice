// APCS Title: d123. B2-Sequence
// APCS Complexity: O(N^2)
// APCS Tag: IO Optimization, Conditionals, Vector
// APCS Difficulty: 2
// APCS Note: https://app.notion.com/p/d123-B2-Sequence-39a43be958cd80afa452f1cad1d030b8?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, cnt = 0;

    while(cin >> n){

        vector<int> v(n);
        vector<bool> is_sum(20005, false);
        bool is_b2 = true;
        cnt++;

        for (int i = 0; i < n; i++){
            cin >> v[i];

            if (v[i] < 1){
                is_b2 = false;
            }
            if (i > 0){
                if (v[i] <= v[i - 1]){
                    is_b2 = false;
                }
            }
        }

        if (is_b2) {
            for (int i = 0; i < n; i++){
                for (int j = i; j < n; j++){
                    
                    if(is_b2){
                        int current_sum = v[i] + v[j];
                        if (!is_sum[current_sum]){
                            is_sum[current_sum] = 1;
                        }
                        else{
                            is_b2 = false;
                            break;
                        }
                    }
                }
                if (!is_b2) break; // 修正：跳出內層後，外層也要同步 break 剪枝
            }
        }

        if (is_b2){
            cout << "Case #" << cnt << ": It is a B2-Sequence.\n\n";
        }
        else{
            cout << "Case #" << cnt << ": It is not a B2-Sequence.\n\n";
        }
    }

    return 0;
}