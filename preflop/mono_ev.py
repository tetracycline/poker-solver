#!/usr/bin/env python3
"""For each monotonicity violation, report per-action EV (bb, given the node is reached) of the two hands,
using the saved GTO strategies as locks. Shows whether the cell is a near-indifferent mix or a real preference."""
import json, sys, numpy as np, pfsolve as S
from analyze import violations
f = sys.argv[1]; d = json.load(open(f)); P = S.default_params(); P['rake'] = 'norake' not in f
root, nodes = S.build(); byname = {n.name: n for n in nodes}
for n in nodes: n.lock = np.array(d['nodes'][n.name]['strat'])
S._RE_CACHE = {}
def find(n, name, r):
    if n.kind != 'dec': return None
    if n.name == name: return n, r
    p = n.seat
    for k, ch in enumerate(n.kids):
        rr = r.copy(); rr[p] = r[p] * n.lock[:, k]; x = find(ch, name, rr)
        if x: return x
def action_evs(name):
    n, r = find(root, name, np.ones((6, 169))); p = n.seat
    vals = [S.ev_profile(ch, r, P)[p] for ch in n.kids]
    fi = n.acts.index('fold'); inv = n.kids[fi].inv[p]
    cw = -vals[fi] / inv                       # counterfactual weight per hand
    return n.acts, [np.where(cw > 1e-15, v / np.where(cw > 1e-15, cw, 1), np.nan) for v in vals]
ix = {h: i for i, h in enumerate(S.NAMES)}
for v in violations(d):
    node, a, b = v[0], v[1], v[2]; acts, ev = action_evs(node)
    fmt = lambda h: ' '.join(f'{acts[k]}={ev[k][ix[h]]:+.2f}' for k in range(len(acts)))
    print(f'{node:24s} {a:4s} [{fmt(a)}]   {b:4s} [{fmt(b)}]')
