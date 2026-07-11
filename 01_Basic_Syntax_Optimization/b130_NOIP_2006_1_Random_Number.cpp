#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    while(cin >> n){

        vector<int> v(n, 0);

        for (int i = 0; i < n; i++){
            cin >> v[i];
        }

        sort(v.begin(), v.end());

        v.erase(unique(v.begin(), v.end()), v.end());

        cout << v.size() << '\n';
        for (int i = 0; i < v.size(); i++){
            if (i) cout << ' ';
            cout << v[i];
        }

        cout << '\n';
    }

    return 0;
}