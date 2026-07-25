#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    for (int i = 0; i < n; i++){

        int a[7], b[7];
        bool A = false, B = false, C = false;

        cin >> a[0] >> a[1] >> a[2] >> a[3] >> a[4] >> a[5] >> a[6];
        cin >> b[0] >> b[1] >> b[2] >> b[3] >> b[4] >> b[5] >> b[6];

        A = (a[1] != a[3] && b[1] != b[3] && a[1] == a[5] && b[1] == b[5]);

        B = (a[6] == 1 && b[6] == 0);

        C = (a[1] != b[1] && a[3] != b[3] && a[5] != b[5]);

        if (A && B && C) {
            cout << "None\n";
        }

        else {

            if (!A) cout << 'A';
            if (!B) cout << 'B';
            if (!C) cout << 'C';
        
            cout << '\n';
        }
    }

    return 0;
}