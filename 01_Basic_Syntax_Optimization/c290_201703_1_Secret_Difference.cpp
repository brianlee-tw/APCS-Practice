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