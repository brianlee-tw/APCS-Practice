// APCS Title: a006. 一元二次方程式
// APCS Complexity: O(1)
// APCS Tag: Conditionals, Math Theory
// APCS Difficulty: 1
// APCS Note:

#include<bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    int a,b,c,r1,r2,D;
    cin>>a>>b>>c;

    D = (pow(b, 2) - 4 * a * c);
    r1 = ((-b + sqrt(D)) / (a * 2));
    r2 = ((-b - sqrt(D))/ (a * 2));

    if (D < 0){
        cout << "No real root\n";
    }
    else if (D == 0){
        cout << "Two same roots x=" << r1 << '\n';
    }
    else{
        cout << "Two different roots x1=" << r1 << " , x2=" << r2 <<'\n';
    }
}