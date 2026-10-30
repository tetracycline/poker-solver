import json,sys
R='AKQJT98765432'
def comp(lst):
    s=set(lst);out=[]
    def runs(seq,top):
        o=[];run=[]
        for h in seq+[None]:
            if h in s: run.append(h)
            else:
                if run: o.append(run[0] if len(run)==1 else (run[-1]+'+' if run[0]==top else run[0]+'-'+run[-1]))
                run=[]
        return o
    out+=runs([r+r for r in R],'AA')
    for t in 'so':
        for i in range(12): out+=runs([R[i]+R[j]+t for j in range(i+1,13)],R[i]+R[i+1]+t)
    return ' '.join(out) or '—'
D=json.loads(open('/workspace/poker_mb/preview_3bet_iso_lines/site/learn_data.js').read()[len('window.LD='):-2])
for k,t in D['tb'].items():
    v4=' '.join(f"{h}:{a}" for h,a in t['vs4'].items() if a!='fold')
    print(f"| {t['o']}→{t['h']} | {t['to']}bb | {comp(t['val'])} | {comp(t['semi'])} | {t['pct']['call']}% | {v4} | {t['pf3']}% / {t['p4']}% |")
print()
for k,t in D['iso'].items():
    print(f"| {k.replace('_2limp',' (2 人)')} | {t['size']}bb | {t['pct']}% | {comp(t['core'])} | {t['lc']}/{t['lf']}/{t['lr']} | {dict(fold='棄',limp='補 '+comp(t['limp']),check='過牌')[t['other']]} |")
