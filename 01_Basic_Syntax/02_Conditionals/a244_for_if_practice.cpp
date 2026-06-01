// APCS Title: a244. for + if
// APCS Complexity: O(1)
// APCS Tag: Basic Syntax, Conditionals
// APCS Difficulty: 1
// APCS Note: https://www.notion.so/a244-for-if-36a43be958cd8081aa57f6377251a74d?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

using ll = long long;

int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);

  int n, a;
  ll b, c;
  cin >> n;
  for (int i = 0; i < n; i++) {
    cin >> a >> b >> c;
    if (a == 1)
      cout << b + c << '\n';
    else if (a == 2)
      cout << b - c << '\n';
    else if (a == 3)
      cout << b * c << '\n';
    else if (a == 4)
      cout << b / c << '\n';
  }

  return 0;
}
