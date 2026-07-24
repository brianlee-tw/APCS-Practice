// APCS Title: r488. APCS 彗星撞擊
// APCS Complexity: O(M*S^2)
// APCS Tag: Array
// APCS Difficulty: 3
// APCS Note: https://app.notion.com/p/r488-APCS-202510-M-1-39343be958cd803e8a1ac6fa7d8a4930?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <bits/stdc++.h>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int R, C, D;
    cin >> R >> C >> D;

    vector<vector<int>> height(R, vector<int>(C, D));
    vector<vector<int>> dino(R, vector<int>(C, 0));

    int K;
    cin >> K;
    int dino_count = K;

    for (int i = 0; i < K; i++){ // 讀入恐龍位置

        int r, c;
        cin >> r >> c;

        dino[r][c]++;
        
    }

    int M;
    cin >> M;

    for (int j = 0; j < M; j++){ // 讀入彗星位置

        int a, b, S, d;
        cin >> a >> b >> S >> d;

        int rad = (S - 1) / 2;
        bool is_dino = false;

        for (int m = a - rad; m <= a + rad; m++){
            for (int n = b - rad; n <= b + rad; n++){
                if (m >= 0 && m < R && n >= 0 && n < C){
                    if (dino[m][n] > 0){
                        is_dino = true;
                        dino_count -= dino[m][n];
                        dino[m][n] = 0;
                    }
                }
            }
        }

        if (!is_dino){
            for (int m = a - rad; m <= a + rad; m++){
                for (int n = b - rad; n <= b + rad; n++){

                    if (m >= 0 && m < R && n >= 0 && n < C){
                        height[m][n] -= d;
                    }

                    }
                }
            }
        }
    

    int max_height = INT_MIN;
    int min_height = INT_MAX;

    for (int p = 0; p < height.size(); p++){
        for (int q = 0; q < height[p].size(); q++){

            if (height[p][q] > max_height){
                max_height = height[p][q];
            }

            if (height[p][q] < min_height){
                min_height = height[p][q];
            }

        }
    }

    cout << max_height << ' ' << min_height << ' ' << dino_count;

}