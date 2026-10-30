#!/usr/bin/env python3
"""Build pf_data.js (single source of truth for every preflop chart/drill/lesson on the site).
Inputs: solver GTO (rake), exploit layer, per-action EV (ev.json). Display rules (documented in the site's 說明):
 1. EV repair: if a reached cell's top-frequency action loses >0.10bb vs the best action (unconverged, low reach), display = pure best-EV action.
 2. Monotonic smoothing: along kicker chains (AKs>AQs>..>A2s, same for offsuit), pair chain and high-card chains
    (except natural connector patterns: weaker hand suited gap<=2 / offsuit gap<=1), continue frequency (1-fold)
    must not rise for a weaker hand by >15pp. Violating blocks are pooled (PAV) into a mixed frequency, but ONLY if every changed
    cell is within 0.25bb of indifference (|EV(best continue) - EV(fold)| <= 0.25). Otherwise kept and listed as caveat.
"""
import json, sys, numpy as np
sys.path.insert(0, '/workspace/outputs/poker_solver/preflop')
import os; os.chdir('/workspace/outputs/poker_solver/preflop')
import pfsolve as S
G = json.load(open('gto_rake.json')); E = json.load(open('/workspace/outputs/poker_solver/robust_v1/exploit_robust.json')); GN = json.load(open('gto_norake.json'))
EVJ = json.load(open('/workspace/outputs/poker_solver/robust_v1/ev_robust.json'))
N = G['names']; IX = {n: i for i, n in enumerate(N)}; RK = '23456789TJQKA'
NC = np.array([6 if len(n) == 2 else 4 if n[2] == 's' else 12 for n in N], float)
EXN = {}
for h in E['heroes'].values(): EXN.update(h['nodes'])
root, nodes = S.build()
# ---- sizing meta from the tree ----
META = {}
for n in nodes:
    p = n.seat
    # invested before acting = inv of fold child if terminal else (rfi): blinds
    k0 = n.kids[0]
    inv = k0.inv if k0.kind != 'dec' else None
    def first_inv(c):
        while c.kind == 'dec': c = c.kids[0]
        return c.inv
    if inv is None: inv = first_inv(k0)
    pot = float(inv.sum()); mine = float(inv[p]); mx = float(inv.max())
    to = {}
    for a, c in zip(n.acts, n.kids):
        if a == 'fold': continue
        ci = c.inv if c.kind != 'dec' else first_inv(c.kids[0]) if a != 'open' else None
        if a == 'open':
            cc = c
            while cc.kind == 'dec': cc = cc.kids[0]
            to[a] = float(cc.inv[p])
        elif c.kind == 'dec':  # raise -> opponent decision; fold child of that has our raise
            to[a] = float(first_inv(c)[p])
        else:
            to[a] = float(c.inv[p])
    META[n.name] = dict(seat=S.SEATS[p], acts=n.acts, pot=round(pot, 2), mine=round(mine, 2), tocall=round(mx - mine, 2), to={a: round(v, 2) for a, v in to.items()})

def nm(a, b, t): return RK[a] * 2 if a == b else RK[max(a, b)] + RK[min(a, b)] + t
CHAINS = []
for hi in range(12, 0, -1):
    for t in 'so': CHAINS.append(('kick', [nm(hi, lo, t) for lo in range(0, hi)]))
CHAINS.append(('pair', [RK[r] * 2 for r in range(13)]))
for lo in range(0, 12):
    for t in 'so': CHAINS.append(('high', [nm(hi, lo, t) for hi in range(lo + 1, 13)]))
def gap(h): return RK.index(h[0]) - RK.index(h[1]) - 1
def natural(typ, w):
    if typ != 'high' or len(w) == 2: return False
    return (w[2] == 's' and gap(w) <= 2) or (w[2] == 'o' and gap(w) <= 1)
MINR = 0.05; THR = 0.15; TOL = 0.25
log = {'evfix': [], 'smoothed': [], 'kept': []}

def process(name, ver, strat, reach, ev):
    acts = META[name]['acts']; fi = acts.index('fold'); A = len(acts)
    S_ = np.array(strat, float); R = np.array(reach, float)
    EVa = np.array([[np.nan if x is None else x for x in row] for row in ev], float)
    flags = {}; S0 = np.array(strat, float).copy()
    # 1. EV repair: drop any action (freq>=5%) that loses >0.25bb vs the best action; if the top action loses >0.10bb, use pure best
    for i in range(169):
        if R[i] <= 0.0 or np.isnan(EVa[i]).any(): continue
        b = int(np.nanargmax(EVa[i])); m = int(np.argmax(S_[i])); row = S_[i].copy()
        bad = [j for j in range(A) if row[j] >= 0.05 and EVa[i, b] - EVa[i, j] > 0.25]
        if bad or EVa[i, b] - EVa[i, m] > 0.10:
            for j in bad: row[j] = 0
            if row.sum() < 1e-9 or EVa[i, b] - EVa[i, int(np.argmax(row))] > 0.10: row = np.zeros(A); row[b] = 1
            row = row / row.sum()
            log['evfix'].append((ver, name, N[i], [round(x, 2) for x in S_[i]], [round(x, 2) for x in row], [round(x, 2) for x in EVa[i]], round(R[i], 3)))
            S_[i] = row; flags[i] = 'evfix'
    def cont(i): return 1 - S_[i, fi]
    def cgap(i):
        e = EVa[i]; return max(e[j] for j in range(A) if j != fi) - e[fi]
    def setc(i, m, ref=None):
        own = S_[i].copy(); own[fi] = 0
        if own.sum() > 0.01: c = own / own.sum()
        else:
            nb = S_[ref].copy(); nb[fi] = 0; c = nb / nb.sum()
        new = c * m; new[fi] = 1 - m; S_[i] = new; flags[i] = 'mix'
    # 2. PAV smoothing with tolerance
    for rnd in range(6):
        changed = False
        for typ, ch in CHAINS:
            cs = [h for h in ch if R[IX[h]] >= MINR]
            if len(cs) < 2: continue
            if typ == 'high':   # only fill dips: a cell lower than BOTH chain neighbours by >15pp
                for w_, c_, s_ in zip(cs, cs[1:], cs[2:]):
                    i = IX[c_]; lo_n = min(cont(IX[w_]), cont(IX[s_]))
                    if lo_n - cont(i) > THR:
                        if abs(cgap(i)) <= TOL:
                            own = S_[i].copy(); own[fi] = 0
                            nb = S_[IX[s_]].copy(); nb[fi] = 0
                            c = own / own.sum() if own.sum() > 0.01 else nb / nb.sum()
                            new = c * lo_n; new[fi] = 1 - lo_n
                            log['smoothed'].append((ver, name, 'dip', N[i], round(cont(i), 2), round(lo_n, 2), round(cgap(i), 2)))
                            S_[i] = new; flags[i] = 'mix'; changed = True
                        elif abs(cgap(IX[w_])) <= TOL and cont(IX[w_]) - cont(i) > THR:   # lower the weaker neighbour instead
                            log['smoothed'].append((ver, name, 'dip-lower', N[IX[w_]], round(cont(IX[w_]), 2), round(cont(i), 2), round(cgap(IX[w_]), 2)))
                            setc(IX[w_], cont(i), i); changed = True
                        else:
                            k_ = (ver, name, (N[i],))
                            if k_ not in [tuple(x[:3]) for x in log['kept']]: log['kept'].append((ver, name, (N[i],), [round(cont(i), 2)], [round(cgap(i), 2)]))
                continue
            # blocks: list of [cells], weighted mean
            blocks = [[IX[h]] for h in cs]
            def mean(b): w = NC[b] * R[b]; return float((np.array([cont(i) for i in b]) * w).sum() / w.sum())
            while True:   # merge the span of the worst violating pair (any weaker block > any stronger block by >THR)
                best = None
                for x in range(len(blocks)):
                    for y in range(x + 1, len(blocks)):
                        d_ = mean(blocks[x]) - mean(blocks[y])
                        if d_ > THR and (best is None or d_ > best[0]): best = (d_, x, y)
                if best is None: break
                _, x, y = best
                blocks[x:y + 1] = [sum(blocks[x:y + 1], [])]
            for b in blocks:
                if len(b) < 2: continue
                m = mean(b)
                ok = all(abs(cgap(i)) <= TOL or abs(cont(i) - m) < 0.02 for i in b)
                if not ok:
                    cv = [cont(i) for i in b]
                    up = list(np.maximum.accumulate(cv)); dn = list(np.minimum.accumulate(cv[::-1]))[::-1]
                    done = False
                    for tgt, tag in ((up, 'raise-stronger'), (dn, 'lower-weaker')):
                        if all(abs(cgap(i)) <= TOL or abs(cont(i) - t) < 0.02 for i, t in zip(b, tgt)):
                            ref = b[int(np.argmax(cv))]
                            for i, t in zip(b, tgt):
                                if abs(cont(i) - t) >= 0.02:
                                    log['smoothed'].append((ver, name, typ + '-' + tag, N[i], round(cont(i), 2), round(t, 2), round(cgap(i), 2))); setc(i, t, ref)
                            changed = True; done = True; break
                    if done: continue
                    key = (ver, name, tuple(N[i] for i in b))
                    if key not in [tuple(x[:3]) for x in log['kept']]:
                        log['kept'].append((ver, name, tuple(N[i] for i in b), [round(cont(i), 2) for i in b], [round(cgap(i), 2) for i in b]))
                    continue
                # composition of continue actions in block
                comp = np.zeros(A); 
                for i in b: comp += NC[i] * R[i] * S_[i]
                comp[fi] = 0; comp = comp / comp.sum() if comp.sum() > 0 else comp
                for i in b:
                    if abs(cont(i) - m) < 0.02: continue
                    own = S_[i].copy(); own[fi] = 0
                    c = own / own.sum() if own.sum() > 0.01 else comp
                    new = c * m; new[fi] = 1 - m
                    log['smoothed'].append((ver, name, typ, N[i], round(cont(i), 2), round(m, 2), round(cgap(i), 2)))
                    S_[i] = new; flags[i] = 'mix'; changed = True
        if not changed: break
    S_ = np.round(S_ * 100).astype(int)
    for i in range(169):  # fix rounding to sum 100
        d = 100 - S_[i].sum(); S_[i, int(np.argmax(S_[i]))] += d
    w = NC * R; tot = w.sum()
    freq = {a: round(float((w * S_[:, k] / 100).sum() / tot * 100), 1) for k, a in enumerate(acts)}
    evc = [[None if np.isnan(x) else int(round(x * 100)) for x in row] for row in EVa]
    fl = {}
    for k, v in flags.items():
        o = np.round(S0[k] * 100).astype(int); o[int(np.argmax(o))] += 100 - o.sum()
        fl[str(k)] = [v, o.tolist()]
    return dict(s=S_.tolist(), r=[int(round(x * 100)) for x in R], ev=evc, fl=fl, freq=freq)

out = {'ver': 'v8-1030', 'names': N, 'nodes': {}, 'heroes': {}, 'pool': {}}
for name in G['nodes']:
    g = G['nodes'][name]; x = EXN[name]
    out['nodes'][name] = dict(META[name], gto=process(name, 'gto', g['strat'], g['reach'], EVJ['gto'][name]),
                              exp=process(name, 'exp', x['strat'], x['reach'], EVJ['exp'][name]),
                              norake={a: round(v * 100, 1) for a, v in GN['nodes'][name]['freq'].items()})
for h, x in E['heroes'].items(): out['heroes'][h] = dict(gain=round(x['gain_bb100'], 1), ev_exp=round(100 * x['ev_exploit'], 1), ev_gto=round(100 * x['ev_gto_vs_pool'], 1))
for k, v in E['pool_info'].items(): out['pool'][k] = dict(t={a: round(p * 100, 1) for a, p in v['target'].items()}, n=v['n'], src=v['src'])
cnt = {}
for v in ('gto', 'exp'):
    cnt[v] = dict(mix=sum(1 for n in out['nodes'].values() for f in n[v]['fl'].values() if f[0] == 'mix'),
                  evfix=sum(1 for n in out['nodes'].values() for f in n[v]['fl'].values() if f[0] == 'evfix'))
out['build'] = dict(counts=cnt, kept=len(log['kept']), tol_bb=TOL, thr_pp=int(THR * 100))
out['params'] = dict(iters=G['meta']['iters'], nashconv_mbb=0.08, rake='5% cap 10bb, no flop no drop', hands_pool=2334487)

js = 'window.PF=' + json.dumps(out, separators=(',', ':'), ensure_ascii=False) + ';'

json.dump(out, open('/workspace/outputs/poker_solver/robust_v1/pf_data_stage1.json', 'w'), separators=(',', ':'), ensure_ascii=False)
json.dump(log, open('/workspace/outputs/poker_solver/robust_v1/smooth_log.json', 'w'), ensure_ascii=False, indent=0)
print('size', len(js) / 1e3, 'KB; evfix', len(log['evfix']), 'smoothed cells', len(log['smoothed']), 'kept blocks', len(log['kept']))
for x in log['kept']: print('KEPT', x)
for x in log['evfix']: print('EVFIX', x)
