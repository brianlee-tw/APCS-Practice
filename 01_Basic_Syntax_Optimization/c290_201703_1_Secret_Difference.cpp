// APCS Title: c290. 祕密差
// APCS Complexity: O(N)
// APCS Tag: String, Loops
// APCS Difficulty: 1
// APCS Note: https://app.notion.com/p/c290-3a743be958cd80e8bd87f98245058fcf?v=36a43be958cd8075b3ac000c2c628f5d&source=copy_link
// APCS Date: 26-07-24

#include <iostream>
#include <string>
#include <cmath>

using namespace std;

int main() {

    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string n;
    if (!(cin >> n)) return 0;

    int sum_odd = 0; 
    int sum_even = 0;

    for (size_t i = 0; i < n.length(); i++) {
   
        int digit = n[i] - '0';
        
        if (i % 2 == 0) {
            sum_odd += digit; 
        } else {
            sum_even += digit;
        }
    }

    cout << abs(sum_odd - sum_even) << '\n';

    return 0;
}