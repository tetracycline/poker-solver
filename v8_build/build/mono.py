import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _PRE=_os.path.join(_HERE,'..','..','preflop')
import json,numpy as np
RK='23456789TJQKA'
G=json.load(open(_os.path.join(_PRE,'gto_rake.json')));E=json.load(open(_os.path.join(_PRE,'exploit_rake.json')))
EV=json.load(open(_os.path.join(_HERE,'ev.json')))
N=G['names'];IX={n:i for i,n in enumerate(N)}
EXN={}
for h in E['heroes'].values(): EXN.update(h['nodes'])
def nm(a,b,t):
    return RK[a]*2 if a==b else RK[max(a,b)]+RK[min(a,b)]+t
def chains():
    C=[]
    for hi in range(12,0,-1):
        for t in 'so': C.append(('kick',[nm(hi,lo,t) for lo in range(0,hi)]))  # weak->strong
    for lo in range(0,12):
        for t in 'so': C.append(('high',[nm(hi,lo,t) for hi in range(lo+1,13)]))
    C.append(('pair',[RK[r]*2 for r in range(13)]))
    return C
CH=chains()
def cont(acts,s): return 1-s[acts.index('fold')]
def viols(acts,S,R,thr=0.15,minr=0.05):
    out=[]
    for typ,ch in CH:
        cs=[h for h in ch if R[IX[h]]>=minr]
        for w,st in zip(cs,cs[1:]):
            d=cont(acts,S[IX[w]])-cont(acts,S[IX[st]])
            if d>thr: out.append((typ,w,st,round(d,2)))
    return out
if __name__=='__main__':
    for ver,src in (('gto',G['nodes']),('exp',EXN)):
        tot=0
        for k,v in src.items():
            vs=viols(v['acts'],v['strat'],v['reach'])
            for typ,w,st,d in vs:
                ew=EV[ver][k][IX[w]];es=EV[ver][k][IX[st]];fi=v['acts'].index('fold')
                gw=max(x for j,x in enumerate(ew) if j!=fi)-ew[fi]; gs=max(x for j,x in enumerate(es) if j!=fi)-es[fi]
                print(ver,k,typ,w,st,d,'gap_w %.2f gap_s %.2f'%(gw,gs),'reach',v['reach'][IX[w]],v['reach'][IX[st]])
                tot+=1
        print(ver,'total',tot)
