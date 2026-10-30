#!/usr/bin/env python3
"""Pool action counts at every postflop decision, same coarse keys as gto_post.py.
SRP: pc=BB, pa in UTG/HJ/CO/BTN (BB=OOP). 3BP: 3-bettor OOP (SB/BB) vs IP caller. stk>=40, heads-up to flop."""
import os, sys, pickle, json
from collections import defaultdict, Counter
H = '/workspace/outputs/poker_solver/read_v1/data/hu.pkl'
def btok(x): return 'bS' if x <= 0.55 else 'bB' if x <= 1.2 else 'bO'
WIN = {1: ((0.25, 0.42), (0.6, 0.9)), 2: ((0.4, 0.6), (0.8, 1.2)), 3: ((0.4, 0.6), (0.8, 1.2))}
def mtok(x, s):
    (a, b), (c, d) = WIN[s]
    if a <= x <= b: return 'bS'
    if c <= x <= d: return 'bB'
    if x > 1.2: return 'bO'
    return 'b?'
def spot(r):
    if r['stk'] < 40: return None
    if r['t'] == 'SRP' and r['pc'] == 'BB' and r['pa'] in ('UTG', 'HJ', 'CO', 'BTN') and r['ip'] == 'A': return 'SRP'
    if r['t'] == '3BP' and r['ip'] == 'C' and r['pa'] in ('SB', 'BB'): return '3BP'
    return None
def run():
    os.nice(19)
    R = pickle.load(open(H, 'rb'))
    cnt = {'SRP': defaultdict(Counter), '3BP': defaultdict(Counter)}; nh = Counter()
    cntm = {'SRP': defaultdict(Counter), '3BP': defaultdict(Counter)}
    cntl = {'SRP': defaultdict(Counter), '3BP': defaultdict(Counter)}
    for r in R:
        sp = spot(r)
        if not sp: continue
        nh[sp] += 1; ipr = r['ip']
        streets = {1: [], 2: [], 3: []}; done = []
        cur = 1; toks = []
        lines = []  # per street token lists
        st_toks = {1: [], 2: [], 3: []}; mt = {1: [], 2: [], 3: []}; bad = False
        for (s, role, a, x, ai) in r['ac']:
            pl = 'IP' if role == ipr else 'OOP'
            facing = bool(st_toks[s]) and st_toks[s][-1] not in ('x', 'c', 'f')
            if a == 'b': t = btok(x)
            elif a == 'r': t = 'r'
            else: t = a
            key = '/'.join(' '.join(st_toks[k]) for k in range(1, s + 1))
            cnt[sp][(pl, key)][t] += 1
            m = mtok(x, s) if a == 'b' else t
            # cntl: coarse history, but the bet being faced (if any) and the action taken use size-matched tokens
            ok = True; kl = [list(st_toks[k]) for k in range(1, s + 1)]
            if facing:
                lm = mt[s][-1] if mt[s] else 'b?'
                j = max(i for i, q in enumerate(st_toks[s]) if q not in ('x', 'c', 'f'))
                lm = mt[s][j]
                if lm == 'b?': ok = False
                elif st_toks[s][j] != 'r': kl[-1][j] = lm
            mm = mtok(x, s) if a == 'b' else t
            if ok and mm != 'b?': cntl[sp][(pl, '/'.join(' '.join(q) for q in kl))][mm] += 1
            if not bad:
                cntm[sp][(pl, '/'.join(' '.join(mt[k]) for k in range(1, s + 1)))][m] += 1
            if m == 'b?': bad = True
            mt[s].append(m)
            st_toks[s].append(t)
            if t == 'f': break
    out = {sp: {f'{k[0]}|{k[1]}': dict(v) for k, v in d.items()} for sp, d in cnt.items()}
    outm = {sp: {f'{k[0]}|{k[1]}': dict(v) for k, v in d.items()} for sp, d in cntm.items()}
    outl = {sp: {f'{k[0]}|{k[1]}': dict(v) for k, v in d.items()} for sp, d in cntl.items()}
    json.dump({'n': nh, 'cnt': out, 'cntm': outm, 'cntl': outl}, open('data/pool_counts.json', 'w'))
    print(nh, {sp: len(v) for sp, v in out.items()})
if __name__ == '__main__': run()
