#include <stdio.h>
#include "eval7.h"
// brute-force check: count category frequencies over all 7-card hands sample vs known distribution
int main(){ long cnt[9]={0}; long n=0; int c[7]; unsigned long long s=88172645463325252ULL;
 for(long t=0;t<20000000;t++){ unsigned long long u=0; for(int k=0;k<7;k++){ int x; do{ s^=s<<13;s^=s>>7;s^=s<<17; x=s%52;}while(u>>x&1); u|=1ULL<<x; c[k]=x;} cnt[eval7(c,7)>>20]++; n++; }
 const char*nm[]={"high","pair","2pair","trips","straight","flush","boat","quads","sf"};
 double ex[]={0.174,0.438,0.235,0.0483,0.0462,0.0303,0.026,0.00168,0.000311};
 for(int i=0;i<9;i++) printf("%s %.5f (exp %.5f)\n",nm[i],(double)cnt[i]/n,ex[i]); }
