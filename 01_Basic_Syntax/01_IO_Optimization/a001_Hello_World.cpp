// APCS Title: a001. 哈囉
// APCS Complexity: O(1)
// APCS Tag: 基礎輸入輸出, 字串處理
// APCS Difficulty: 1
// APCS Note:https://www.notion.so/a001-36a43be958cd80c48115f59d68f70a5f?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link

#include <iostream>
using namespace std;

int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
  string s;
  while (cin >> s) {
    cout << "hello, " << s << endl;
  }
  return 0;
}
