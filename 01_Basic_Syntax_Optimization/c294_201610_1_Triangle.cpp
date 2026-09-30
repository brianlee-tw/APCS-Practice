#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    vector<int> v(3);
    cin >> v[0] >> v[1] >> v[2];
    sort(v.begin(), v.end());

    int sq[3] = {v[0] * v[0], v[1] * v[1], v[2] * v[2]};

    cout << v[0] << ' ' << v[1] << ' ' << v[2] << '\n';

    if (v[0] + v[1] <= v[2]) {
        cout << "No\n";
    }
    else if (sq[0] + sq[1] < sq[2]) {
        cout << "Obtuse\n";
    }
    else if (sq[0] + sq[1] == sq[2]) {
        cout << "Right\n";
    }
    else {
        cout << "Acute\n";
    }

    return 0;
}