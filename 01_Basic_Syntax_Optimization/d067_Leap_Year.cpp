// APCS Title: d067. 一個都不能少
// APCS Complexity: O(1)
// APCS Tag: Conditionals
// APCS Difficulty: 1
// APCS Note:

#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int y;
    cin>>y;

    if(y % 400 == 0){
        cout<<"a leap year";
    }
    else if(y % 100 == 0){
        cout<<"a normal year";
    }
    else if(y % 4 == 0){
        cout<<"a leap year";
    }
    else{
        cout<<"a normal year";
    }
}