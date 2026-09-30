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