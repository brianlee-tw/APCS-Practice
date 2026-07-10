#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int r, c;
    while(cin >> r >> c){

    int a[r][c];
    int t[c][r];

    for (int i = 0; i < r; i++){
        for (int j = 0; j < c; j++){
            cin >> a[i][j];
            t[j][i] = a[i][j];
        }
    }

    for (int k = 0; k < c; k++){
        for (int l = 0; l < r; l++){
            cout << t[k][l] << " ";
        }
        cout << endl;
    }

    }
    return 0;
}