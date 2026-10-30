#!/usr/bin/env python3
"""Aggregate postflop v1 solver strategies (GTO + pool-exploit) into beginner buckets:
spot-group x flop texture x decision category x hand class -> action frequencies (combo-reach weighted)."""
import json, gzip, glob, os, sys, numpy as np
from collections import defaultdict
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from handclass import hand_class, texture, turn_type, HC
D = '/workspace/postflop/pages_v1_postflop/data'
# spot -> (pfr side, group for IP player, group for OOP player)
SPOT = {'BTN_BB': ('SRP_IP', 'SRP_BB'), 'CO_BB': ('SRP_IP', 'SRP_BB'), 'HJ_BB': ('SRP_IP', 'SRP_BB'), 'UTG_BB': ('SRP_IP', 'SRP_BB'),
        'SB_BB': ('SRP_BBvsSB', 'SRP_SB'), 'SB3_BTN': ('3BP_caller', '3BP_3bettor'), 'BB3_BTN': ('3BP_caller', '3BP_3bettor')}
BETCATS = {'f_cbet', 'barrel', 'delay', 'probe', 'r_barrel', 'r_stab', 'stab', 'f_float'}
def agroup(a):
    if a == 'x': return 'x'
    if a in ('f', 'c'): return a
    if a in ('r',): return 'r'
    if a == 'a': return 'big'
    n = int(a[1:]); return 'small' if n <= 50 else 'big'
def one(path):
    spot = path.split('/')[-2]; d = json.load(gzip.open(path)); flop = d['flop']; tx = texture(flop)
    acc = defaultdict(lambda: defaultdict(float))
    for ver in ('gto', 'exp'):
        for n in d['v'][ver]:
            c = n['c']; p = int(n['p']); grp = SPOT[spot][0] if p == 1 else SPOT[spot][1]
            acts = n['a']; na = len(acts); hs = n['h']; s = n['s']; w = n['w']; b = n['b']
            st = {6: 'flop', 8: 'turn', 10: 'river'}[len(b)]
            facing = c not in BETCATS
            tt = turn_type(b[:6], b[6:8]) if len(b) >= 8 else '-'
            for i in range(len(hs) // 4):
                wi = w[i] / 100.0
                if wi <= 0: continue
                hc = hand_class(hs[4 * i:4 * i + 4], b)
                for k, a in enumerate(acts):
                    g = agroup(a); f = s[i * na + k] / 100.0
                    if facing and g == 'big': g = 'r'
                    for key in ((ver, grp, tx, c, hc), (ver, grp, 'ALL', c, hc), (ver, grp, 'TT_' + tt, c, hc), (ver, grp, 'ST_' + st, c, hc)):
                        acc[key][g] += wi * f
                for key in ((ver, grp, tx, c, hc), (ver, grp, 'ALL', c, hc), (ver, grp, 'TT_' + tt, c, hc), (ver, grp, 'ST_' + st, c, hc)):
                    acc[key]['_w'] += wi
    return {'|'.join(k): dict(v) for k, v in acc.items()}
if __name__ == '__main__':
    os.nice(19)
    files = sorted(glob.glob(f'{D}/*/*.json.gz'))
    with Pool(int(os.environ.get('NP', '2'))) as pool: parts = pool.map(one, files, chunksize=2)
    tot = defaultdict(lambda: defaultdict(float))
    for p in parts:
        for k, v in p.items():
            for a, x in v.items(): tot[k][a] += x
    out = {}
    for k, v in tot.items():
        w = v.pop('_w'); out[k] = dict(n=round(w, 1), **{a: round(x / w, 3) for a, x in v.items()})
    json.dump(out, open('data/lines_agg.json', 'w'), ensure_ascii=False)
    print(len(files), 'files', len(out), 'keys')
