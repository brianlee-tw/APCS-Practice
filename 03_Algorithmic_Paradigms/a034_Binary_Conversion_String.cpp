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
