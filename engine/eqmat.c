// 169x169 preflop all-in equity matrix by Monte Carlo over exact combo pairs (card removal exact).
// Output: eq169.bin (float64 eq[i][j] = equity of class i vs class j, ties count half), and compat counts.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "eval7.h"
static const char *R="23456789TJQKA";
int ncls=0; int combos[169][12][2]; int ncomb[169]; char name[169][4];
static inline uint64_t xs(uint64_t *s){ *s^=*s<<13; *s^=*s>>7; *s^=*s<<17; return *s; }
int main(int argc,char**argv){
  int S = argc>1? atoi(argv[1]) : 20000;
  // class order: same as trainer ALL: i=12..0, j=12..0; pair if i==j, i>j suited (R[i]R[j]s), i<j offsuit R[j]R[i]o
  for(int i=12;i>=0;i--) for(int j=12;j>=0;j--){
    int k=ncls++; ncomb[k]=0;
    if(i==j){ sprintf(name[k],"%c%c",R[i],R[i]); for(int a=0;a<4;a++) for(int b=a+1;b<4;b++){ combos[k][ncomb[k]][0]=i*4+a; combos[k][ncomb[k]++][1]=i*4+b; } }
    else if(i>j){ sprintf(name[k],"%c%cs",R[i],R[j]); for(int s=0;s<4;s++){ combos[k][ncomb[k]][0]=i*4+s; combos[k][ncomb[k]++][1]=j*4+s; } }
    else { sprintf(name[k],"%c%co",R[j],R[i]); for(int a=0;a<4;a++) for(int b=0;b<4;b++) if(a!=b){ combos[k][ncomb[k]][0]=j*4+a; combos[k][ncomb[k]++][1]=i*4+b; } }
  }
  static double EQ[169][169]; static int CP[169][169];
  #pragma omp parallel for schedule(dynamic)
  for(int x=0;x<169;x++){
    uint64_t seed=0x9E3779B97F4A7C15ULL*(x+1);
    for(int y=x;y<169;y++){
      // compatible combo pairs
      int pairs[144][2]; int np=0;
      for(int a=0;a<ncomb[x];a++) for(int b=0;b<ncomb[y];b++){
        int *p=combos[x][a],*q=combos[y][b];
        if(p[0]==q[0]||p[0]==q[1]||p[1]==q[0]||p[1]==q[1]) continue;
        pairs[np][0]=a; pairs[np++][1]=b; }
      CP[x][y]=CP[y][x]=np;
      if(np==0){ EQ[x][y]=EQ[y][x]=0.5; continue; }
      double w=0; int per = (S+np-1)/np;
      for(int t=0;t<np;t++){
        int *p=combos[x][pairs[t][0]],*q=combos[y][pairs[t][1]];
        uint64_t used = (1ULL<<p[0])|(1ULL<<p[1])|(1ULL<<q[0])|(1ULL<<q[1]);
        for(int s=0;s<per;s++){
          int bd[5]; uint64_t u=used;
          for(int k=0;k<5;k++){ int c; do{ c=xs(&seed)%52; }while(u>>c&1); u|=1ULL<<c; bd[k]=c; }
          int h1[7]={p[0],p[1],bd[0],bd[1],bd[2],bd[3],bd[4]}, h2[7]={q[0],q[1],bd[0],bd[1],bd[2],bd[3],bd[4]};
          int e1=eval7(h1,7),e2=eval7(h2,7);
          w += e1>e2?1.0: e1==e2?0.5:0.0;
        }
      }
      double e=w/(double)(np*per); EQ[x][y]=e; EQ[y][x]=1-e;
    }
  }
  FILE*f=fopen("eq169.bin","wb"); fwrite(EQ,sizeof(EQ),1,f); fclose(f);
  f=fopen("compat169.bin","wb"); fwrite(CP,sizeof(CP),1,f); fclose(f);
  f=fopen("names169.txt","w"); for(int k=0;k<169;k++) fprintf(f,"%s\n",name[k]); fclose(f);
  printf("AA vs KK %.4f  AKs vs QQ %.4f  72o vs AA %.4f  AKo vs 22 %.4f\n",EQ[0][14],EQ[1][28],EQ[168-0][0],EQ[13][168]);
  return 0;
}
