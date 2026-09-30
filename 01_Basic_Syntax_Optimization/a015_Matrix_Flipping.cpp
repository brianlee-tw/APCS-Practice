#include <bits/stdc++.h>

using namespace std;

int a[105][105];

int main() {

    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int r, c;
    while (cin >> r >> c) {

        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) {
                cin >> a[i][j];
            }
        }

        for (int k = 0; k < c; k++) {
            for (int l = 0; l < r; l++) {
                cout << a[l][k] << " ";
            }
            cout << '\n';
        }
    }
    return 0;
}