"""Variant GTO solve: same model, but offsuit Q9o/Q8o/K9o/K8o-type hands get the same playability as J9o (0.90) instead of junk (0.84).
Tests whether 'J9o defends but Q9o folds' is a realization-table artifact. Output: gto_playfix.json (analysis only)."""
import sys; sys.path.insert(0, '/workspace/outputs/poker_solver/preflop')
import numpy as np, pfsolve as S
RK = S.RK
for i, n in enumerate(S.NAMES):
    if len(n) == 3 and n[2] == 'o':
        a, b = RK.index(n[0]), RK.index(n[1])
        if a in (10, 11) and b >= 6 and b < 8: S.PLAY0[i] = max(S.PLAY0[i], 0.90)
P = S.default_params(); P['rake'] = True
root, nodes, hist = S.solve(P, 3000, log_every=1000)
rf = S.dump(root, '/workspace/outputs/poker_solver/rfi_audit/gto_playfix.json', dict(params=P, iters=3000, hist=hist, note=__doc__))
for k in ['UTGrfi', 'HJrfi', 'COrfi', 'BTNrfi', 'SBrfi', 'BTNopen>BB', 'SBopen>BB']: print(k, {a: round(100 * x, 1) for a, x in rf[k]['freq'].items()})
