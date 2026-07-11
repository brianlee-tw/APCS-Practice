#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    while(cin >> n){

        set<int> s;
        int num;

        for (int i = 0; i < n; i++){
            cin >> num;
            s.insert(num);
        }


        cout << s.size() << '\n';

        auto it = s.begin();
        while (it != s.end()){
            cout << *it;
            it++;
            if (it != s.end()) cout << ' ';
        }

        cout << '\n';
    }

    return 0;
}