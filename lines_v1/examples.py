#!/usr/bin/env python3
"""Pick concrete drill hands (hand + board + spot) for each rule from the solver data; the answer always comes from rules.json."""
import json, gzip, glob, os, random, sys
from collections import defaultdict
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from handclass import hand_class, texture
from lines import SPOT, BETCATS, agroup, D
R = json.load(open('data/rules.json')); RID = {r['id']: r for r in R}
def keyfor(g, c, tx, st, hc):
    for d in (tx, 'ST_' + st, 'ALL'):
        k = f'{g}|{c}|{d}|{hc}'
        if k in RID: return k
    return None
def one(path):
    rnd = random.Random(hash(path) & 0xffff); spot = path.split('/')[-2]; d = json.load(gzip.open(path)); tx = texture(d['flop'])
    out = defaultdict(list)
    for ver in ('exp', 'gto'):
        for n in d['v'][ver]:
            c = n['c']; p = int(n['p']); g = SPOT[spot][0] if p == 1 else SPOT[spot][1]; b = n['b']
            st = {6: 'flop', 8: 'turn', 10: 'river'}[len(b)]; acts = n['a']; na = len(acts); hs = n['h']; s = n['s']; w = n['w']
            facing = c not in BETCATS
            idx = list(range(len(hs) // 4)); rnd.shuffle(idx); got = {}
            for i in idx:
                if w[i] < 50: continue
                hc = hand_class(hs[4 * i:4 * i + 4], b); k = keyfor(g, c, tx, st, hc)
                if not k: continue
                r = RID[k]
                if got.get(k, 0) >= 1: continue
                if (ver == 'exp') == (g == 'SRP_IP' and c == 'r_stab'): continue   # gto-only cells use gto nodes
                pr = {}
                for j, a in enumerate(acts):
                    gg = agroup(a); gg = 'r' if facing and gg == 'big' else gg; pr[gg] = pr.get(gg, 0) + s[i * na + j] / 100
                q = pr.get(r['ans'], 0)
                if q < 0.3 and not r.get('note'): continue
                out[k].append(dict(h=hs[4 * i:4 * i + 4], b=b, spot=spot, l=n['l'], pot=n['pot'], q=round(q, 2)))
                got[k] = got.get(k, 0) + 1
    return dict(out)
if __name__ == '__main__':
    os.nice(19)
    with Pool(2) as pool: parts = pool.map(one, sorted(glob.glob(f'{D}/*/*.json.gz')), chunksize=2)
    ex = defaultdict(list)
    for p in parts:
        for k, v in p.items(): ex[k] += v
    rnd = random.Random(7); out = {}
    for k, v in ex.items():
        rnd.shuffle(v); v.sort(key=lambda e: -min(e['q'], 0.6)); seen = set(); keep = []
        for e in v:
            sig = (e['h'], e['b'][:6])
            if sig in seen: continue
            seen.add(sig); keep.append(e)
            if len(keep) >= 6: break
        out[k] = keep
    json.dump(out, open('data/examples.json', 'w'))
    print(len(out), 'rules with examples; missing:', [r['id'] for r in R if r['id'] not in out])
