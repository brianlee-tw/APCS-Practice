#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string line;
    stringstream ss;

    while(getline(cin, line)){
        if (line.empty()) continue; // 過濾可能出現的空白行

        ss << line;

        int n, a[3005] = {0}, d[3005] = {0};
        bool is_jolly = true;

        ss >> n;

        for(int i = 0; i < n; i++){
            ss >> a[i]; 

            if (i > 0){
                int diff = abs(a[i] - a[i - 1]);
                // 確保差值落在 1 ~ n-1 區間內才記錄
                if (diff < n && diff > 0){
                    d[diff] = 1;
                }
            }
        }

        for (int i = 1; i < n; i++){
            if (d[i] == 0){
                cout << "Not jolly\n";
                is_jolly = false;
                break;
            }
        }

        if (is_jolly){
            cout << "Jolly\n";
        }

        ss.str("");
        ss.clear();
    }

    return 0;
}