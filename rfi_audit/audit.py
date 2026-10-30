#!/usr/bin/env python3
"""RFI audit: hero best response at each RFI seat vs node-locked NL2 pool under perturbed scenarios.
Analysis only; reads ../preflop (pfsolve, exploit) and writes results.json here."""
import sys, os, json, numpy as np, time
sys.path.insert(0, '/workspace/outputs/poker_solver/preflop')
import pfsolve as S, exploit as X
P = S.default_params(); P['rake'] = True
G = X.GTO; NAMES = S.NAMES; W = S.W
root, nodes = S.build(); BY = {n.name: n for n in nodes}
HEROES = ['UTG', 'HJ', 'CO', 'BTN', 'SB']
POOL_OPEN = {s: X.PRE[s]['open_raise'] / 100 for s in HEROES}

# ---------- realization penalty for hero (beginner) ----------
def weak_off(n): return len(n) == 3 and n[2] == 'o' and not (S.RK.index(n[1]) >= 8)
WEAK = np.array([weak_off(n) for n in NAMES])
_EC = {}
def realized_role(ptype, role, pen):
    key = (ptype, role, pen)
    if key in _EC: return _EC[key]
    PL = S.PLAY0 ** P.get('spread', 1.0); k = P['k'][ptype]; sk = S.STR / 0.5
    Rip = PL ** k * sk ** (P['d_ip'] * k); Roop = P['base_oop'][ptype] * PL ** (k * P['oop_pow']) * sk ** (P['d_oop'] * k)
    if pen > 0 and ptype in ('SRP', '3BP'):
        if role == 'oop': Roop = Roop * (1 - pen) * np.where(WEAK, 1 - pen, 1.0)
        if role == 'ip': Rip = Rip * np.where(WEAK, 1 - pen / 2, 1.0)
    num = S.EQ * Rip[:, None]; E = num / (num + (1 - S.EQ) * Roop[None, :]); _EC[key] = E; return E
HERO = {'seat': None, 'pen': 0.0}
_orig_tv = S.term_vals
def term_vals(t, r, P_):
    if t.kind != 'flop' or HERO['pen'] == 0 or HERO['seat'] not in t.active: return _orig_tv(t, r, P_)
    a, b = t.active; ip = S.ip_of(a, b); oop = b if ip == a else a; h = HERO['seat']
    role = 'ip' if ip == h else 'oop'
    s = (W[None, :] * r).sum(1); out = np.zeros((6, 169)); pot = t.inv.sum()
    F = np.prod([s[j] for j in range(6) if j not in (a, b)]); pr_ip = S.PJ @ r[oop]; pr_oop = S.PJ @ r[ip]
    def hu(net, Eip, Eoop, inv):
        return (F * (net * ((S.PJ * Eip) @ r[oop]) - inv[ip] * pr_ip), F * (net * ((S.PJ * Eoop) @ r[ip]) - inv[oop] * pr_oop))
    E = realized_role(t.ptype, role, HERO['pen'])
    vi, vo = hu(pot - S.drop_flop(pot, P_), E, 1 - E.T, t.inv)
    phi = P_.get('stackoff', {}).get(t.ptype, 0.0)
    if phi > 0:
        inv2 = t.inv.copy(); inv2[a] = inv2[b] = 100.0; pot2 = inv2.sum()
        ai, ao = hu(pot2 - S.drop_allin(pot2, P_), S.EQ, S.EQ, inv2); vi = (1 - phi) * vi + phi * ai; vo = (1 - phi) * vo + phi * ao
    out[ip] = vi; out[oop] = vo
    both = r[ip] @ S.PJ @ r[oop]
    for f in range(6):
        if f in (a, b): continue
        out[f] = -t.inv[f] * W * np.prod([s[j] for j in range(6) if j not in (a, b, f)]) * both
    return out
S.term_vals = term_vals

# ---------- pool locks with modified defender targets ----------
def is_vs_open(name):
    p = name.split('>'); return len(p) == 2 and p[0].endswith('open') and not p[1].endswith('3b')
def shaped_lock(reach, acts, tgt, gstrat):
    """like linear_lock but hands ordered by GTO continue prob (then raw strength) instead of raw strength only"""
    fi = acts.index('fold'); key = (1 - gstrat[:, fi]) + 0.5 * gstrat[:, acts.index('3bet')] + 0.01 * S.STR
    w = W * reach; tot = w.sum(); idx = np.argsort(-key); L = np.zeros((169, len(acts)))
    seq = sorted(acts, key=lambda a: X.ORDER[a]); bounds = []; c = 0
    for a in seq: bounds.append((a, c, c + tgt.get(a, 0))); c += tgt.get(a, 0)
    acc = 0
    for i in idx:
        lo, hi = acc / tot, (acc + w[i]) / tot; acc += w[i]
        if hi - lo < 1e-12: L[i, fi] = 1; continue
        for a, b0, b1 in bounds: L[i, acts.index(a)] += max(0, min(hi, b1) - max(lo, b0)) / (hi - lo)
        L[i] /= L[i].sum()
    return L
def make_locks(hero, alpha=0.0, adapt=0.0, hero_open=None, bbsb_fold=None, shape=None):
    locks = {}
    def rec(n, r):
        if n.kind != 'dec': return
        p = n.seat; g = np.array(G['nodes'][n.name]['strat']); t = X.pool_target(n.name, n.acts)
        if t and n.name.startswith(hero + 'open') and is_vs_open(n.name):
            tg = dict(t[0]); gf = G['nodes'][n.name]['freq']
            tg = {a: tg[a] + alpha * (gf[a] - tg[a]) for a in tg}
            if bbsb_fold is not None and n.name == 'SBopen>BB':
                a_ = (t[0]['fold'] - bbsb_fold) / (t[0]['fold'] - gf['fold'])
                tg = {a: t[0][a] + a_ * (gf[a] - t[0][a]) for a in tg}
            if adapt and hero_open is not None:
                d = adapt * (hero_open - POOL_OPEN[hero])          # fold drops by `adapt` pts per pt of extra width
                f0 = tg['fold']; f1 = min(max(f0 - d, 0.05), 0.95); rest = 1 - f0
                tg = {'fold': f1, 'call': tg['call'] / rest * (1 - f1), '3bet': tg['3bet'] / rest * (1 - f1)}
            if shape == 'gtostrat': L = g
            elif shape == 'gto': L = shaped_lock(r[p], n.acts, tg, g)
            else: L = X.linear_lock(r[p], n.acts, tg)
        elif t: L = X.linear_lock(r[p], n.acts, t[0])
        else: L = g
        locks[n.name] = L
        for k, ch in enumerate(n.kids):
            rr = r.copy(); rr[p] = r[p] * L[:, k]; rec(ch, rr)
    rec(root, np.ones((6, 169)))
    return locks

def rfi_dev(hero, locks, pen=0.0):
    """per-hand EV(open)-EV(fold) in bb given folded to hero; hero best-responds later; returns (dEV, P(folded to))"""
    h = S.SEATS.index(hero); HERO['seat'] = h; HERO['pen'] = pen; _EC.clear(); S._RE_CACHE = {}
    for n in nodes: n.lock = None if n.seat == h else locks[n.name]
    r = np.ones((6, 169)); pf = 1.0
    for j in range(h):
        L = locks[S.SEATS[j] + 'rfi']; r[j] = L[:, 0]; pf *= float((W * L[:, 0]).sum())
    n = BY[hero + 'rfi']
    vf = S.br(n.kids[0], r, P, h); vo = S.br(n.kids[1], r, P, h)
    return (vo - vf) / (W * pf), pf

def scen(hero, alpha=0.0, adapt=0.0, pen=0.0, bbsb_fold=None, shape=None):
    if not adapt:
        return rfi_dev(hero, make_locks(hero, alpha, bbsb_fold=bbsb_fold, shape=shape), pen)
    ho = POOL_OPEN[hero]
    for it in range(30):                       # fixed point: defenders adapt to hero's actual width
        d, pf = rfi_dev(hero, make_locks(hero, alpha, adapt, ho, bbsb_fold, shape), pen)
        new = float((W * (d > 0)).sum())
        if abs(new - ho) < 0.002: break
        ho = 0.5 * ho + 0.5 * new
    return d, pf

SCEN = [('base', dict()), ('a25', dict(alpha=.25)), ('a50', dict(alpha=.5)), ('a75', dict(alpha=.75)), ('a100', dict(alpha=1.0)),
        ('adapt25', dict(adapt=.25)), ('adapt50', dict(adapt=.5)), ('pen5', dict(pen=.05)), ('pen10', dict(pen=.10)),
        ('a50_pen5', dict(alpha=.5, pen=.05)), ('adapt25_pen5', dict(adapt=.25, pen=.05)), ('adapt50_pen10', dict(adapt=.5, pen=.10)),
        ('shape', dict(shape='gto')), ('shape_a50', dict(shape='gto', alpha=.5)), ('shape_pen5', dict(shape='gto', pen=.05)), ('shape_adapt25_pen5', dict(shape='gto', adapt=.25, pen=.05)), ('gtostrat', dict(shape='gtostrat'))]
if __name__ == '__main__':
    res = {}
    for hero in HEROES:
        res[hero] = {}
        sc = SCEN + ([('bbsb50', dict(bbsb_fold=.50)), ('bbsb45', dict(bbsb_fold=.45))] if hero == 'SB' else [])
        for nm, kw in sc:
            t0 = time.time(); d, pf = scen(hero, **kw)
            res[hero][nm] = dict(dev=[float(x) for x in d], pf=pf, open=float((W * (d > 0)).sum()))
            print(hero, nm, f"open {100*res[hero][nm]['open']:.1f}%  ({time.time()-t0:.1f}s)", flush=True)
    res['gto_open'] = {h: [float(row[1]) for row in G['nodes'][h + 'rfi']['strat']] for h in HEROES}
    res['exploit_open'] = {h: [float(row[1]) for row in X.json.load(open('/workspace/outputs/poker_solver/preflop/exploit_rake.json'))['heroes'][h]['nodes'][h + 'rfi']['strat']] for h in HEROES}
    res['names'] = NAMES
    json.dump(res, open('/workspace/outputs/poker_solver/rfi_audit/results.json', 'w'))
