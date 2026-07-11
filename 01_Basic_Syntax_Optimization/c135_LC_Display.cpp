// APCS Title: c135. 00706 - LC-Display
// APCS Complexity: O(L * n)
// APCS Tag: Loops, Vector, String
// APCS Difficulty: 3
// APCS Note: https://app.notion.com/p/c135-LC-Display-39a43be958cd80d38f69da3406f6f9c7?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-11

#include <iostream>
#include <string>
#include <vector>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    string s;
    
    // 七段顯示器狀態：[0]頂, [1]上左, [2]上右, [3]中, [4]下左, [5]下右, [6]底
    vector<vector<int>> v(10, vector<int>(7));
    v[0] = {1, 1, 1, 0, 1, 1, 1};
    v[1] = {0, 0, 1, 0, 0, 1, 0};
    v[2] = {1, 0, 1, 1, 1, 0, 1};
    v[3] = {1, 0, 1, 1, 0, 1, 1};
    v[4] = {0, 1, 1, 1, 0, 1, 0};
    v[5] = {1, 1, 0, 1, 0, 1, 1};
    v[6] = {1, 1, 0, 1, 1, 1, 1};
    v[7] = {1, 0, 1, 0, 0, 1, 0};
    v[8] = {1, 1, 1, 1, 1, 1, 1};
    v[9] = {1, 1, 1, 1, 0, 1, 1};
    
    while (cin >> n >> s) {
        if (n == 0 && s == "0") break;

        vector<char> chars(s.begin(), s.end());

        for (int i = 0; i < chars.size(); i++) {
            int idx = chars[i] - '0';
            cout << " " << (v[idx][0] ? string(n, '-') : string(n, ' ')) << " ";
            if (i < chars.size() - 1) cout << " ";
        }
        cout << '\n';

        for (int row = 0; row < n; row++) {
            for (int i = 0; i < chars.size(); i++) {
                int idx = chars[i] - '0';
                cout << (v[idx][1] ? '|' : ' ') << string(n, ' ') << (v[idx][2] ? '|' : ' ');
                if (i < chars.size() - 1) cout << " ";
            }
            cout << '\n';
        }

        for (int i = 0; i < chars.size(); i++) {
            int idx = chars[i] - '0';
            cout << " " << (v[idx][3] ? string(n, '-') : string(n, ' ')) << " ";
            if (i < chars.size() - 1) cout << " ";
        }
        cout << '\n';

        for (int row = 0; row < n; row++) {
            for (int i = 0; i < chars.size(); i++) {
                int idx = chars[i] - '0';
                cout << (v[idx][4] ? '|' : ' ') << string(n, ' ') << (v[idx][5] ? '|' : ' ');
                if (i < chars.size() - 1) cout << " ";
            }
            cout << '\n';
        }

        for (int i = 0; i < chars.size(); i++) {
            int idx = chars[i] - '0';
            cout << " " << (v[idx][6] ? string(n, '-') : string(n, ' ')) << " ";
            if (i < chars.size() - 1) cout << " ";
        }
        cout << '\n' << '\n'; 
    }

    return 0;
}