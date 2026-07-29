// APCS Title: a130. Google Is Feeling Lucky
// APCS Complexity: O(T)
// APCS Tag: Array, Vector, String, Struct
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/a130-Google-is-Lucky-3ac43be958cd800cb815e655bb7a89d8?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-28

#include <iostream>
#include <vector>
#include <string>
#include <climits>

using namespace std;

struct Website {
    string url;
    int score;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    while (cin >> t) {
        for (int j = 1; j <= t; j++) {

            vector<Website> sites(10);
            int max_score = INT_MIN;

            for (int i = 0; i < 10; i++) {
                cin >> sites[i].url >> sites[i].score;
                if (sites[i].score > max_score) {
                    max_score = sites[i].score;
                }
            }

            cout << "Case #" << j << ":\n";

            for (const auto &site : sites) {
                if (site.score == max_score) {
                    cout << site.url << '\n';
                }
            }
        }
    }

    return 0;
}