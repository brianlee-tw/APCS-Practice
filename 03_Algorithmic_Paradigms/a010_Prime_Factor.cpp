#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

using ll = long long;
int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  while (cin >> n) {
    bool first = true;
    for (int i = 2; i * i <= n; i++) {

      if (n % i == 0) {

        int cnt = 0;

        while (n % i == 0) {
          n /= i;
          cnt++;
        }

        if (!first) {
          cout << " * ";
        }

        if (cnt > 1) {
          cout << i << "^" << cnt;
        }

        else {
          cout << i;
        }

        first = false;
      }
    }
    if (n > 1) {
      if (!first) {
        cout << " * ";
      }
      cout << n;
    }

    cout << "\n";
  }
  return 0;
}
