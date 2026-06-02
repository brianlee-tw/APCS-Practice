// APCS Title: a034. 二進位制轉換
// APCS Complexity: O(\log n)
// APCS Tag: Basic Syntax, Loops, Math Theory
// APCS Difficulty: 2
// APCS Note: https://www.notion.so/a034-36a43be958cd80a49057f8b8925ed00d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <algorithm>
#include <iostream>
#include <string>

using namespace std;

int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(0);

  int n;
  while (cin >> n) {
    // 特判 0 的狀況，處理完 continue
    if (n == 0) {
      cout << "0\n";
      continue;
    }

    string ans = "";
    while (n > 0) {
      ans.push_back((n & 1) + '0');
      n >>= 1;
    }

    reverse(ans.begin(), ans.end());
    cout << ans << "\n";
  }
  return 0;
}
