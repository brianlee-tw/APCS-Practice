// APCS Title: b428. 凱撒密碼
// APCS Complexity: O(1)
// APCS Tag: Math Theory, String
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/b428-3ac43be958cd80e4ac9ee7188c4a8419?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-29

#include <iostream>
#include <string>

using namespace std;

int main()
{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string a, b;

    while (cin >> a >> b)
    {

        int k = (b[0] - a[0] + 26) % 26;

        cout << k << "\n";
    }

    return 0;
}