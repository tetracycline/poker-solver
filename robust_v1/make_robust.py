"""Interim deploy data: hero RFI locked to the audited robust ranges (UTG/HJ/CO = recommended >=7/9 scenarios; BTN/SB = core 9/9),
then hero re-solves everything downstream (CFR best response vs NL2 pool locks, same as exploit.py). Writes exploit_robust.json (same schema)."""
import json, sys, time, numpy as np
sys.path.insert(0, '/workspace/outputs/poker_solver/preflop')
import os; os.chdir('/workspace/outputs/poker_solver/preflop')
import pfsolve as S, exploit as X
F = json.load(open('/workspace/outputs/poker_solver/rfi_audit/final.json'))
USE = {'UTG': 'rec_cells', 'HJ': 'rec_cells', 'CO': 'rec_cells', 'BTN': 'core_cells', 'SB': 'core_cells'}
E0 = json.load(open('exploit_rake.json'))
P = S.default_params(); P['rake'] = True
root, nodes = S.build(); seat_of = {n.name: n.seat for n in nodes}
locks, info = X.build_pool_locks(root)
out = dict(E0); out['heroes'] = dict(E0['heroes']); out['meta'] = dict(E0['meta'], robust=dict(src='rfi_audit/final.json', sets=USE))
for hero, key in USE.items():
    h = S.SEATS.index(hero); t0 = time.time(); cells = set(F[hero][key])
    rl = np.array([[0.0, 1.0] if n in cells else [1.0, 0.0] for n in S.NAMES])
    lk = {k: v for k, v in locks.items() if seat_of[k] != h}; lk[hero + 'rfi'] = rl
    r, ns, hist = S.solve(P, 400, locks=lk, root_nodes=(root, nodes), quiet=True)
    rf = S.reach_freq(r)
    ev_ex = float(S.ev_profile(r, np.ones((6, 169)), P)[h].sum())
    for n in ns: n.lock = np.array(X.GTO['nodes'][n.name]['strat']) if n.seat == h else locks[n.name]
    ev_gto = float(S.ev_profile(r, np.ones((6, 169)), P)[h].sum())
    out['heroes'][hero] = dict(ev_exploit=ev_ex, ev_gto_vs_pool=ev_gto, ev_br=E0['heroes'][hero]['ev_br'], gain_bb100=100 * (ev_ex - ev_gto),
        nodes={k: dict(acts=v['acts'], freq={a: round(x, 4) for a, x in v['freq'].items()}, strat=[[round(float(x), 3) for x in row] for row in v['strat']],
                       reach=[round(float(x), 3) for x in v['reach_range']]) for k, v in rf.items() if seat_of[k] == h})
    for n in ns: n.lock = None
    print(hero, 'open %.1f%%' % (100 * rf[hero + 'rfi']['freq']['open']), f'EV robust {100*ev_ex:+.2f} vs full exploit {100*E0["heroes"][hero]["ev_exploit"]:+.2f} GTO-vs-pool {100*ev_gto:+.2f} ({time.time()-t0:.0f}s)', flush=True)
json.dump(out, open('/workspace/outputs/poker_solver/robust_v1/exploit_robust.json', 'w'), separators=(',', ':'))
