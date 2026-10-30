#!/usr/bin/env python3
"""Per-hand per-action EV (bb, whole-hand, given the node is reached; hero reach forced to 1 at node)
for every preflop node, for GTO (all seats GTO) and exploit (hero = exploit strat, others = NL2 pool locks)."""
import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _PRE=_os.path.join(_HERE,'..','..','preflop')
import sys, json, time, numpy as np
sys.path.insert(0, _PRE)
import os; os.chdir(_PRE)
import pfsolve as S, exploit as X
P = S.default_params(); P['rake'] = True
G = json.load(open('gto_rake.json')); E = json.load(open('exploit_rake.json'))
root, nodes = S.build(); seat_of = {n.name: n.seat for n in nodes}
pool_locks, info = X.build_pool_locks(root)
def find(n, name, r):
    if n.kind != 'dec': return None
    if n.name == name: return n, r
    p = n.seat
    for k, ch in enumerate(n.kids):
        rr = r.copy(); rr[p] = r[p] * n.lock[:, k]; x = find(ch, name, rr)
        if x: return x
def action_evs(name):
    n, r = find(root, name, np.ones((6, 169))); p = n.seat
    r = r.copy(); r[p] = np.ones(169)
    vals = [S.ev_profile(ch, r, P)[p] for ch in n.kids]
    sc = (S.W[None, :] * r).sum(1); cw = S.W * np.prod([sc[j] for j in range(6) if j != p])
    return n.acts, [np.where(cw > 1e-15, v / np.where(cw > 1e-15, cw, 1), np.nan) for v in vals]
out = {'gto': {}, 'exp': {}}
S._RE_CACHE = {}
t0 = time.time()
for n in nodes: n.lock = np.array(G['nodes'][n.name]['strat'])
for n in nodes:
    acts, ev = action_evs(n.name); out['gto'][n.name] = [[None if np.isnan(e[i]) else round(float(e[i]), 3) for e in ev] for i in range(169)]
print('gto done', time.time() - t0, flush=True)
expnodes = {}
for h in E['heroes'].values(): expnodes.update(h['nodes'])
for h in range(6):
    for n in nodes: n.lock = np.array(expnodes[n.name]['strat']) if n.seat == h else pool_locks[n.name]
    for n in nodes:
        if n.seat != h: continue
        acts, ev = action_evs(n.name); out['exp'][n.name] = [[None if np.isnan(e[i]) else round(float(e[i]), 3) for e in ev] for i in range(169)]
print('exp done', time.time() - t0, len(out['exp']), flush=True)
out['pool_strat'] = {k: [[round(float(x), 3) for x in row] for row in v] for k, v in pool_locks.items()}
json.dump(out, open(_os.path.join(_HERE,'ev.json'), 'w'), separators=(',', ':'))
