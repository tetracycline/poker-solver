// Simple, exact 7-card hand evaluator. Cards 0..51: rank = c>>2 (0=2..12=A), suit = c&3.
// Returns an int where larger = stronger. category<<20 | kicker bits.
#include <stdint.h>
static inline int top5(uint32_t m){ // keep highest 5 bits of 13-bit mask
  int r=0,n=0; for(int i=12;i>=0&&n<5;i--) if(m>>i&1){r|=1<<i;n++;} return r; }
static inline int straight_hi(uint32_t m){ // m 13-bit rank mask; returns high rank+1 or 0
  uint32_t x = (m<<1) | (m>>12 & 1); // ace low at bit0
  for(int hi=13;hi>=4;hi--){ uint32_t w=0x1F<<(hi-4); if((x&w)==w) return hi; }
  return 0; }
static inline int eval7(const int *c, int n){
  uint32_t sm[4]={0,0,0,0}, all=0; int cnt[13]={0};
  for(int i=0;i<n;i++){ int r=c[i]>>2,s=c[i]&3; sm[s]|=1u<<r; all|=1u<<r; cnt[r]++; }
  for(int s=0;s<4;s++) if(__builtin_popcount(sm[s])>=5){ int sh=straight_hi(sm[s]); if(sh) return (8<<20)|sh; return (5<<20)|top5(sm[s]); }
  int quad=-1,trips[2]={-1,-1},nt=0,pairs[3]={-1,-1,-1},np=0;
  for(int r=12;r>=0;r--){ if(cnt[r]==4) quad=r; else if(cnt[r]==3){ if(nt<2) trips[nt++]=r; } else if(cnt[r]==2){ if(np<3) pairs[np++]=r; } }
  if(quad>=0){ uint32_t k=all&~(1u<<quad); int hi=31-__builtin_clz(k); return (7<<20)|(quad<<4)|hi; }
  if(nt>=1 && (nt>=2||np>=1)){ int p = nt>=2? trips[1] : pairs[0]; if(nt>=2 && np>=1 && pairs[0]>p) p=pairs[0]; return (6<<20)|(trips[0]<<4)|p; }
  int sh=straight_hi(all); if(sh) return (4<<20)|sh;
  if(nt==1){ uint32_t k=all&~(1u<<trips[0]); int a=31-__builtin_clz(k); k&=~(1u<<a); int b=31-__builtin_clz(k); return (3<<20)|(trips[0]<<8)|(a<<4)|b; }
  if(np>=2){ uint32_t k=all&~(1u<<pairs[0])&~(1u<<pairs[1]); int a=31-__builtin_clz(k); return (2<<20)|(pairs[0]<<8)|(pairs[1]<<4)|a; }
  if(np==1){ uint32_t k=all&~(1u<<pairs[0]); int t=0,s=8; for(int i=0;i<3;i++){int a=31-__builtin_clz(k); k&=~(1u<<a); t|=a<<s; s-=4;} return (1<<20)|(pairs[0]<<12)|t; }
  return top5(all);
}
