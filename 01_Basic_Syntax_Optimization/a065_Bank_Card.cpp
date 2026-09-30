#include <iostream>
#include <string>
#include <cmath>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s;
    while (cin >> s) {
        for (int i = 1; i < 7; i++) {
            cout << abs(s[i] - s[i - 1]);
        }
        cout << "\n";
    }

    return 0;
}