// APCS Title: c022. Odd Sum
// APCS Complexity: O(N)
// APCS Tag: IO Optimization, Loops, Math Theory
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/c022-Odd-Sum-39043be958cd8010b382cce73b1a44e3?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int n;
    cin >> n;

    for (int i = 1; i <= n; i++){

        int a, b, total = 0;
        cin >> a;
        cin >> b;

        if (a % 2 == 0){
            a++;
        }

        for (int j = a; j <= b; j += 2){
            total += j;
        }

        cout << "Case " << i << ": " << total << '\n';
    }
}