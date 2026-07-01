// APCS Title: e835. 表演座位
// APCS Complexity: O(1)
// APCS Tag: Conditionals, Math Theory
// APCS Difficulty: 1
// APCS Note:

#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int n,a,r,c;
    cin >> n;

    if (n <= 2500){
        a = 1;
        r = (n + 24) / 25;
        c = (n - 1) % 25 + 1;
    }
    else if (n > 2500 && n <= 7500){
        a = 2;
        r = (n - 2500 + 49) / 50;
        c = (n - 1) % 50 + 1;
    }
    else if (n > 7500){
        a = 3;
        r = (n - 7500 + 24) / 25;
        c = (n - 1) % 25 + 1;
    }

    cout << a << " " << r << " " << c << endl;
}