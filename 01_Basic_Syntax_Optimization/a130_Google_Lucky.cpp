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