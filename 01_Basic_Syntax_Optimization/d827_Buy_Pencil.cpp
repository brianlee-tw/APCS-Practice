// APCS Title: d827. 買鉛筆
// APCS Complexity: O(1)
// APCS Tag: Math Theory
// APCS Difficulty: 1
// APCS Note:

#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int n;
    cin>>n;

    cout<< (n/12) * 50 + (n%12) * 5;
}