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