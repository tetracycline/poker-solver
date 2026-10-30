#!/usr/bin/env python3
"""Hand reading from pool showdowns with censoring correction.
For every villain action node (HW perspective), estimate villain's holding distribution:
  - HW folds are censoring that is independent of villain's cards -> dropped and renormalised at HW decision points
  - villain's later actions depend on his cards -> kept as a mixture weighted by observed frequencies
  - villain folding later = his class is never seen -> reported as a separate 'G' (gave up later) share
Leaves are showdown hands; each gets the weight of its path. Output data/reads_raw.pkl."""
import pickle, json, sys, os, math
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vclass import fine, GROUP, texture, cards, RV
os.nice(19)
R = pickle.load(open('data/hu.pkl', 'rb'))
RK = '23456789TJQKA'
def pre(h):
    a, b = h[:2], h[2:]; x, y = RK.index(a[0]), RK.index(b[0])
    if x < y: x, y = y, x; a, b = b, a
    return RK[x] * 2 if x == y else RK[x] + RK[y] + ('s' if a[1] == b[1] else 'o')
def views(r):
    t = r['t']
    if t == 'SRP' and r['pc'] == 'BB' and r['pa'] in ('UTG', 'HJ', 'CO', 'BTN'):
        yield 'SRP_IP', 'A'; yield 'SRP_BB', 'C'
    elif t == '3BP':
        yield '3BP_3b_' + ('IP' if r['ip'] == 'A' else 'OOP'), 'A'; yield '3BP_call_' + ('IP' if r['ip'] == 'C' else 'OOP'), 'C'
    elif t == 'ISO':
        yield 'ISO_' + ('IP' if r['ip'] == 'A' else 'OOP'), 'A'
def tok(role, hw, act, x, ai):
    who = 'H' if role == hw else 'V'
    if act == 'b':
        if who == 'H': return 'Hb' + ('1' if x <= 0.55 else '2')
        return 'Vb' + ('S' if x <= 0.55 else 'B' if x <= 1.2 else 'O')
    if act == 'r':
        if who == 'H': return 'Hr'
        return 'Vr' + ('n' if x <= 2.6 and not ai else 'g')
    return who + act
def coarse(s): return s.replace('Hb1', 'Hb').replace('Hb2', 'Hb')
SPOTS = defaultdict(list)
for i, r in enumerate(R):
    if r['stk'] < 40: continue
    for sp, hw in views(r):
        seq = [(st, tok(role, hw, act, x, ai)) for (st, role, act, x, ai) in r['ac']]
        vh = r['hc'] if hw == 'A' else r['ha']
        SPOTS[sp].append((i, seq, vh))
print({k: len(v) for k, v in SPOTS.items()}, flush=True)
OUT = {}
for sp, lst in SPOTS.items():
    nid = {}; N = []; CH = []; LEAF = []; MISS = []; TOK = []; STR = []; TEXL = []
    def node(key, t, s, tx):
        if key in nid: return nid[key]
        k = len(N); nid[key] = k; N.append(0); CH.append({}); LEAF.append([]); MISS.append(0); TOK.append(t); STR.append(s); TEXL.append(tx); return k
    for (i, seq, vh) in lst:
        tx = texture(R[i]['bd'])
        cur = node((tx, ''), '', '', tx); N[cur] += 1; s = ''; laststreet = 1
        for (st, t) in seq:
            s = s + ('/' if st != laststreet and s else (' ' if s else '')) + t; laststreet = st
            k = node((tx, s), t, s, tx); CH[cur][t] = k; N[k] += 1; cur = k
        if seq and seq[-1][1] in ('Hf', 'Vf'): continue
        if vh: LEAF[cur].append((i, vh))
        else: MISS[cur] += 1
    print(sp, 'nodes', len(N), flush=True)
    def prop(root):
        leaves = []; give = 0.0; stack = [(root, 1.0)]
        while stack:
            k, w = stack.pop()
            hf = CH[k].get('Hf'); den = N[k] - (N[hf] if hf is not None else 0) - MISS[k]
            if den <= 0: continue
            for t, c in CH[k].items():
                if t == 'Hf': continue
                if t == 'Vf': give += w * N[c] / den; continue
                stack.append((c, w * N[c] / den))
            for lf in LEAF[k]: leaves.append((lf, w / den))
        return leaves, give
    agg = defaultdict(lambda: dict(n=0, raw=[]))
    for k in range(len(N)):
        if not TOK[k].startswith('V') or TOK[k] == 'Vf' or N[k] < 20: continue
        ck = coarse(STR[k])
        for tx in (TEXL[k], 'ALL'):
            a = agg[(tx, ck)]; a['n'] += N[k]; a['raw'].append(k)
    for (tx, ck), a in agg.items():
        if a['n'] < 80: continue
        street = ck.count('/') + 1; L = []; G = 0.0
        for k in a['raw']:
            lv, g = prop(k); f = N[k] / a['n']
            L += [(lf, w * f) for lf, w in lv]; G += g * f
        sw = sum(w for _, w in L)
        if sw <= 0: continue
        ess = sw * sw / sum(w * w for _, w in L)
        fc = Counter(); pc = Counter(); LL = []
        for (i, vh), w in L:
            b = R[i]['bd'][:4 + 2 * street]
            try: c = fine(vh, b)
            except Exception: continue
            fc[c] += w; pc[(pre(vh), c)] += w; LL.append((i, vh, w / sw))
        tot = sum(fc.values()) or 1; obs = 1 - G
        fs = {c: round(v / tot * obs, 4) for c, v in fc.items()}
        gs = Counter()
        for c, v in fs.items(): gs[GROUP[c]] += v
        gs['G'] = G
        OUT[f'{sp}|{tx}|{ck}'] = dict(sp=sp, tx=tx, line=ck, street=street, n=a['n'], nsd=len(L), ess=round(ess, 1),
                                     grp={k: round(v, 4) for k, v in gs.items()}, fine=fs,
                                     top=[(h, c, round(v / tot * obs, 4)) for (h, c), v in pc.most_common(8)], leaves=LL)
    print(sp, 'keys', sum(1 for k in OUT if k.startswith(sp + '|')), flush=True)
    del nid, N, CH, LEAF
pickle.dump(OUT, open('data/reads_raw.pkl', 'wb'))
print('total keys', len(OUT))
