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