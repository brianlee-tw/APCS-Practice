// APCS Title: a065. 提密碼
// APCS Complexity: O(1)
// APCS Tag: String, Array
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/a065-3ac43be958cd80df8a4af97b6039bb04?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-29

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