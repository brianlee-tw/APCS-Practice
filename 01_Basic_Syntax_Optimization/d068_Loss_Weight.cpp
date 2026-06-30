// APCS Title: d068. 該減肥了！
// APCS Complexity: O(1)
// APCS Tag: Conditionals
// APCS Difficulty: 1
// APCS Note:

#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int w;
    cin>>w;

    if(w > 50){
        cout<<w-1;
    }
    else{
        cout<<w;
    }
}