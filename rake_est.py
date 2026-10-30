# HU-flop only. Empirical rake+jackpot drop as function of preflop pot (bb), hands that saw a flop. GG NL2 HHDealer sample.
import sys,re,glob,json
from collections import defaultdict
HU_ONLY=True
B=defaultdict(lambda:[0,0.0,0.0,0.0])
for fn in sys.argv[1:]:
    txt=open(fn,errors='ignore').read()
    for h in txt.split('Poker Hand #')[1:]:
        m=re.search(r'Total pot \$([0-9.]+) \| Rake \$([0-9.]+) \| Jackpot \$([0-9.]+)',h)
        if not m or '*** FLOP' not in h or 'FIRST FLOP' in h: continue
        p,r,j=map(float,m.groups())
        pre=h.split('*** FLOP')[0]
        put=defaultdict(float)
        for ln in pre.splitlines():
            mm=re.match(r'(\S+): posts (?:small|big) blind \$([0-9.]+)',ln)
            if mm: put[mm.group(1)]=float(mm.group(2)); continue
            mm=re.match(r'(\S+): raises \$[0-9.]+ to \$([0-9.]+)',ln)
            if mm: put[mm.group(1)]=float(mm.group(2)); continue
            mm=re.match(r'(\S+): calls \$([0-9.]+)',ln)
            if mm: put[mm.group(1)]+=float(mm.group(2))
        pp=sum(put.values())/0.02
        seats=set(re.findall(r'^(\S+): (?:posts|calls|raises|checks|folds|bets)',pre,re.M)); folded=set(re.findall(r'^(\S+): folds',pre,re.M))
        if HU_ONLY and len(seats-folded)!=2: continue
        nact=len([1 for ln in pre.splitlines() if re.match(r'\S+: (calls|raises)',ln)])
        k=('<4' if pp<4 else '4-7' if pp<7 else '7-12' if pp<12 else '12-20' if pp<20 else '20-35' if pp<35 else '35-60' if pp<60 else '60+')
        b=B[k]; b[0]+=1;b[1]+=pp;b[2]+=(r)/0.02;b[3]+=j/0.02
out={}
for k in ['<4','4-7','7-12','12-20','20-35','35-60','60+']:
    if k in B:
        n,pp,r,j=B[k]; out[k]=dict(n=n,avg_pre_pot=round(pp/n,2),avg_rake_bb=round(r/n,3),avg_jp_bb=round(j/n,3),drop_over_prepot=round((r+j)/pp,4))
print(json.dumps(out,indent=1))
