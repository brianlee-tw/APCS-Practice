#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

using ll = long long;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s;
    while (cin >> s){
        reverse(s.begin(), s.end());

        int result = stoi(s);

        cout << result << "\n";
    }

    return 0;
}