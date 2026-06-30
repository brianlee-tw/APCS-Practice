// APCS Title: d065. 三人行必有我師
// APCS Complexity: O(1)
// APCS Tag: Conditionals
// APCS Difficulty: 1
// APCS Note:

#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int a,b,c;
    cin>>a>>b>>c;
    cout<<max({a,b,c});
}