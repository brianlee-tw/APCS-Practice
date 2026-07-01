// APCS Title: d072. 格瑞哥里的煩惱 (Case 版)
// APCS Complexity: O(1)
// APCS Tag: IO Optimization, Conditionals, Loops
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/d071-EOF-39043be958cd805aacd7e907233cf4c2?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);

    int n, y, cnt = 0;
    cin>>n;

    while (cin >> y) {
        cnt++;

        if (y % 400 == 0) {
            cout << "Case " << cnt << ": a leap year\n";
        } 
        
        else if (y % 100 == 0) {
            cout << "Case " << cnt << ": a normal year\n";
        } 
        
        else if (y % 4 == 0) {
            cout << "Case " << cnt <<  ": a leap year\n";
        } 
        
        else {
            cout << "Case " << cnt <<  ": a normal year\n";
        }
    }
    return 0;
}