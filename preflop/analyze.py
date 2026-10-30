import json,sys
RK='23456789TJQKA'
def load(p): return json.load(open(p))
def cont(node):  # continue (non-fold) prob per class
    a=node['acts']; return [1-row[0] if a[0]=='fold' else 1 for row in node['strat']]
def violations(d, thr=0.15, nodes=None):
    N=d['names']; ix={n:i for i,n in enumerate(N)}; out=[]
    for k,v in d['nodes'].items():
        if nodes and k not in nodes: continue
        reach=v['reach']; c=cont(v)
        def ok(n): return reach[ix[n]]>0.05
        # kicker monotonic: XYs vs XZs with Y>Z
        for hi in range(12,0,-1):
            for t in 'so':
                for lo in range(hi-1,0,-1):
                    a=RK[hi]+RK[lo]+t; b=RK[hi]+RK[lo-1]+t
                    if ok(a) and ok(b) and c[ix[b]]-c[ix[a]]>thr: out.append((k,b,a,round(c[ix[b]],2),round(c[ix[a]],2)))
        for r in range(12,0,-1):
            a=RK[r]*2; b=RK[r-1]*2
            if ok(a) and ok(b) and c[ix[b]]-c[ix[a]]>thr: out.append((k,b,a,round(c[ix[b]],2),round(c[ix[a]],2)))
    return out
def grid(node, N, mode='cont'):
    ix={n:i for i,n in enumerate(N)}; lines=[]
    for i in range(12,-1,-1):
        row=[]
        for j in range(12,-1,-1):
            n = RK[i]*2 if i==j else (RK[i]+RK[j]+'s' if i>j else RK[j]+RK[i]+'o')
            s=node['strat'][ix[n]]; x=1-s[0] if node['acts'][0]=='fold' else 1
            row.append('%3d'%round(100*x))
        lines.append(' '.join(row))
    return '\n'.join(lines)
if __name__=='__main__':
    d=load(sys.argv[1]); v=violations(d)
    print(len(v),'violations >15pp'); [print(x) for x in v[:60]]
    for k in sys.argv[2:]: print(k); print(grid(d['nodes'][k],d['names']))
