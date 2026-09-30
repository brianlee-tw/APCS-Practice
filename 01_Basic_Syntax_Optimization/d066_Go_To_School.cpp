#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int h,m,time;
    cin>>h>>m;

    time = h * 60 + m;

    if(time < 450 || time >= 1020){
        cout << "Off School";
    }
    else{
        cout << "At School";
    }
}