#!/usr/bin/env python3
"""6-max 100bb preflop solver (vectorised CFR over 169 hand classes).

Tree (documented abstraction, see REPORT.md):
  RFI: UTG..BTN fold / open 2.5bb ; SB fold / open 3bb (no limp branch)
  vs open: each later seat in turn fold / call / 3bet. The FIRST seat that calls or 3bets
           makes the pot heads-up; seats behind it are folded (no squeeze / overcall branch).
  3bet sizes: IP 3x open, OOP (SB/BB vs non-blind) 4x open; BB vs SB open = 3x (BB is IP).
  vs 3bet: opener fold / call / 4bet (2.2x the 3bet)
  vs 4bet: 3bettor fold / call / all-in (100bb)
  vs all-in: fold / call
Terminal values:
  fold-out          : winner takes pot (no flop no drop).
  call -> flop (HU) : (pot - drop(pot)) * realized_equity - invested
  all-in called     : (pot - drop_allin) * raw_equity - invested
Realized equity (odds form, keeps the game constant-sum):
  E_a = eq*Ra / (eq*Ra + (1-eq)*Rb),  R = base(position, pot type) * playability(hand)^k(pot type)
"""
import numpy as np, json, sys, os, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); ENG = os.path.join(HERE, '..', 'engine')
NAMES = [l.strip() for l in open(os.path.join(ENG, 'names169.txt'))]
EQ = np.fromfile(os.path.join(ENG, 'eq169.bin'), dtype=np.float64).reshape(169, 169)
CP = np.fromfile(os.path.join(ENG, 'compat169.bin'), dtype=np.int32).reshape(169, 169).astype(np.float64)
PJ = CP / (1326.0 * 1225.0)                                   # joint prob of (class_a, class_b) for two seats
NC = np.array([6 if len(n) == 2 else 4 if n[2] == 's' else 12 for n in NAMES], float)
W = NC / 1326.0                                               # prior of a class for one seat
SEATS = ['UTG', 'HJ', 'CO', 'BTN', 'SB', 'BB']
RK = '23456789TJQKA'
POSTFLOP_ORDER = [4, 5, 0, 1, 2, 3]                            # SB, BB, UTG, HJ, CO, BTN

# ---------------- realization model ----------------
def playability(n):
    """hand-class equity-realization factor on the IP scale (SRP). Heuristic table, see REPORT.md section 2.3.
    Shape follows published EQR studies: suited/connected hands over-realize, dominated offsuit
    high-card hands and offsuit junk under-realize; pairs ~ neutral."""
    if len(n) == 2:
        r = RK.index(n[0]); return 0.95 if r <= 3 else 1.0 if r <= 7 else 1.05   # 22-55 / 66-TT / JJ+
    a, b, s = RK.index(n[0]), RK.index(n[1]), n[2] == 's'
    gap = a - b - 1
    if s:
        p = {0: 1.25, 1: 1.18, 2: 1.12}.get(gap, 1.06)
        if a == 12: p = max(p, 1.15)                       # nut-flush Ax suited
        if b >= 8: p = max(p, 1.18)                        # suited broadway
    else:
        if b >= 8: p = 1.0                                 # offsuit broadway
        elif a == 12: p = 0.86 if b >= 5 else 0.84         # A9o-A2o (domination)
        elif gap == 0: p = 0.95
        elif gap == 1: p = 0.90
        else: p = 0.84
        if b <= 3 and a != 12: p -= 0.08                   # offsuit with a 2-5 kicker
    return p
PLAY0 = np.array([playability(n) for n in NAMES]); PLAY = PLAY0.copy()
STR = (EQ * PJ).sum(1) / PJ.sum(1)                            # equity vs a random hand (hand-strength proxy)
def default_params():
    return dict(stackoff={'4BP': 0.7}, base_oop={'SRP': 0.80, '3BP': 0.88, '4BP': 0.95}, k={'SRP': 1.0, '3BP': 0.6, '4BP': 0.3},
                d_oop=0.5, d_ip=0.25, oop_pow=1.5, spread=1.6, rake=True)
RAKE_TAB = None
def drop_flop(pp, P):
    if not P['rake']: return 0.0
    xs = np.array([2.26, 5.47, 8.39, 16.0, 24.7, 46.92, 147.59]); ys = np.array([.0662, .1189, .1376, .1443, .1347, .0954, .0454])  # data/rake_empirical_hu.json
    return float(np.interp(pp, xs, ys)) * pp
def drop_allin(pp, P):
    return (min(0.05 * pp, 10.0) + 1.0) if P['rake'] else 0.0

_RE_CACHE = {}
def realized(ptype, P):
    """returns matrix E[x,y] = realized equity share of IP hand x vs OOP hand y"""
    key = ptype
    if key in _RE_CACHE: return _RE_CACHE[key]
    PLAY = PLAY0 ** P.get('spread', 1.0)
    k = P['k'][ptype]; sk = (STR / 0.5)
    Rip = PLAY ** k * sk ** (P['d_ip'] * k); Roop = P['base_oop'][ptype] * PLAY ** (k * P['oop_pow']) * sk ** (P['d_oop'] * k)
    num = EQ * Rip[:, None]; den = num + (1 - EQ) * Roop[None, :]
    E = num / den; _RE_CACHE[key] = E; return E

# ---------------- tree ----------------
class Node:
    __slots__ = ('kind', 'seat', 'acts', 'kids', 'inv', 'active', 'ptype', 'name', 'id', 'reg', 'ssum', 'lock')
def mk(kind, **kw):
    n = Node(); n.kind = kind
    for k in Node.__slots__: setattr(n, k, None)
    n.kind = kind
    for k, v in kw.items(): setattr(n, k, v)
    return n
def ip_of(a, b): return a if POSTFLOP_ORDER.index(a) > POSTFLOP_ORDER.index(b) else b

def build(stack=100.0, open_size=2.5, sb_open=3.0, ip3=3.0, oop3=4.0, f4=2.2):
    nodes = []
    def dec(seat, acts, kids, name):
        n = mk('dec', seat=seat, acts=acts, kids=kids, name=name, id=len(nodes)); nodes.append(n); return n
    def term(kind, inv, active, ptype=None):
        return mk(kind, inv=np.array(inv, float), active=active, ptype=ptype)
    def hu_after_3bet(op, y, inv, t3, name):
        # opener op faces 3bet by y to t3
        t4 = round(f4 * t3, 1)
        inv_c = inv.copy(); inv_c[op] = t3
        inv4 = inv.copy(); inv4[op] = t4
        # y vs 4bet
        inv_y_c = inv4.copy(); inv_y_c[y] = t4
        inv_jam = inv4.copy(); inv_jam[y] = stack
        inv_jc = inv_jam.copy(); inv_jc[op] = stack
        n_jam = dec(op, ['fold', 'call'], [term('fold', inv_jam, [y]), term('allin', inv_jc, [op, y])], name + '>4b>jam')
        n_vs4 = dec(y, ['fold', 'call', 'jam'], [term('fold', inv4, [op]), term('flop', inv_y_c, [op, y], '4BP'), n_jam], name + '>4b')
        return dec(op, ['fold', 'call', '4bet'], [term('fold', inv, [y]), term('flop', inv_c, [op, y], '3BP'), n_vs4], name)
    def responders(op, j, inv, osz, name):
        # seat j acts facing open by op (all seats between folded)
        if j > 5: return term('fold', inv, [op])
        blind = j >= 4
        if op == 4 and j == 5: t3 = round(ip3 * osz, 1)        # BB vs SB: BB in position
        else: t3 = round((oop3 if blind else ip3) * osz, 1)
        inv_call = inv.copy(); inv_call[j] = osz
        inv3 = inv.copy(); inv3[j] = t3
        nm = name + '>' + SEATS[j]
        return dec(j, ['fold', 'call', '3bet'], [responders(op, j + 1, inv, osz, name), term('flop', inv_call, [op, j], 'SRP'),
                                                  hu_after_3bet(op, j, inv3, t3, nm + '3b')], nm)
    def rfi(i):
        inv = np.zeros(6); inv[4] = 0.5; inv[5] = 1.0
        if i == 5: return term('fold', inv, [5])
        osz = sb_open if i == 4 else open_size
        inv_o = inv.copy(); inv_o[i] = osz
        return dec(i, ['fold', 'open'], [rfi(i + 1), responders(i, i + 1, inv_o, osz, SEATS[i] + 'open')], SEATS[i] + 'rfi')
    root = rfi(0)
    return root, nodes

# ---------------- CFR ----------------
def term_vals(t, r, P):
    """counterfactual values for all 6 seats (6x169) at terminal t given reach r (6x169)."""
    s = (W[None, :] * r).sum(1)                     # scalar reach of each seat
    pot = t.inv.sum(); out = np.zeros((6, 169))
    act = t.active
    if t.kind == 'fold':
        w = act[0]
        for i in range(6):
            others = np.prod([s[j] for j in range(6) if j != i])
            pay = (pot - t.inv[i]) if i == w else -t.inv[i]
            out[i] = pay * others * W
        return out
    a, b = act; ip = ip_of(a, b); oop = b if ip == a else a
    F = np.prod([s[j] for j in range(6) if j not in (a, b)])
    pr_ip = PJ @ r[oop]; pr_oop = PJ @ r[ip]
    def hu(net, Eip, Eoop, inv):
        return (F * (net * ((PJ * Eip) @ r[oop]) - inv[ip] * pr_ip), F * (net * ((PJ * Eoop) @ r[ip]) - inv[oop] * pr_oop))
    if t.kind == 'flop':
        E = realized(t.ptype, P)
        vi, vo = hu(pot - drop_flop(pot, P), E, 1 - E.T, t.inv)   # Eoop[y,x] share of oop hand y vs ip hand x
        phi = P.get('stackoff', {}).get(t.ptype, 0.0)
        if phi > 0:   # low-SPR pots: a fraction phi of flops end with stacks in at raw equity
            inv2 = t.inv.copy(); inv2[a] = inv2[b] = P.get('stack', 100.0); pot2 = inv2.sum()
            ai, ao = hu(pot2 - drop_allin(pot2, P), EQ, EQ, inv2)
            vi = (1 - phi) * vi + phi * ai; vo = (1 - phi) * vo + phi * ao
    else:
        vi, vo = hu(pot - drop_allin(pot, P), EQ, EQ, t.inv)
    out[ip] = vi; out[oop] = vo
    both = r[ip] @ PJ @ r[oop]
    for f in range(6):
        if f in (a, b): continue
        others = np.prod([s[j] for j in range(6) if j not in (a, b, f)])
        out[f] = -t.inv[f] * W * others * both
    return out

def strat(n):
    if n.lock is not None: return n.lock
    R = np.maximum(n.reg, 0); S = R.sum(1, keepdims=True)
    return np.where(S > 0, R / np.where(S > 0, S, 1), 1.0 / len(n.acts))
def avg(n):
    if n.lock is not None: return n.lock
    S = n.ssum.sum(1, keepdims=True); return np.where(S > 0, n.ssum / np.where(S > 0, S, 1), 1.0 / len(n.acts))

def cfr(n, r, P, it, frozen):
    if n.kind != 'dec': return term_vals(n, r, P)
    p = n.seat; sg = strat(n); vals = []; tot = np.zeros((6, 169))
    for k, ch in enumerate(n.kids):
        rr = r.copy(); rr[p] = r[p] * sg[:, k]
        v = cfr(ch, rr, P, it, frozen); vals.append(v[p]); tot += v if k == 0 else v
    # tot currently sums all children; seat p's value is the strategy-weighted sum instead
    vp = sum(sg[:, k] * vals[k] for k in range(len(n.kids)))
    tot[p] = vp
    if n.lock is None and p not in frozen:
        # DCFR (alpha=1.5, beta=0, gamma=2)
        a = it ** 1.5; pos = a / (a + 1)
        reg = n.reg
        reg *= np.where(reg > 0, pos, 0.5)
        for k in range(len(n.kids)): reg[:, k] += vals[k] - vp
        n.ssum *= (it / (it + 1)) ** 2
        n.ssum += r[p][:, None] * sg
    return tot

def br(n, r, P, seat):
    """best-response values for `seat` vs avg strategies of others (6x169 for seat row only meaningful)"""
    if n.kind != 'dec': return term_vals(n, r, P)[seat]
    p = n.seat
    if p == seat:
        vs = [br(ch, r, P, seat) for ch in n.kids]
        return np.max(np.stack(vs), 0)
    sg = avg(n); v = 0
    for k, ch in enumerate(n.kids):
        rr = r.copy(); rr[p] = r[p] * sg[:, k]; v = v + br(ch, rr, P, seat)
    return v
def ev_profile(n, r, P):
    if n.kind != 'dec': return term_vals(n, r, P)
    p = n.seat; sg = avg(n); tot = np.zeros((6, 169)); vals = []
    for k, ch in enumerate(n.kids):
        rr = r.copy(); rr[p] = r[p] * sg[:, k]; v = ev_profile(ch, rr, P); vals.append(v[p]); tot += v
    tot[p] = sum(sg[:, k] * vals[k] for k in range(len(n.kids)))
    return tot

def exploitability(root, P):
    r0 = np.ones((6, 169)); ev = ev_profile(root, r0, P)
    res = {}
    for s in range(6):
        b = br(root, r0, P, s); res[SEATS[s]] = dict(ev=float(ev[s].sum()), br=float(b.sum()), gain=float(b.sum() - ev[s].sum()))
    return res

def solve(P, iters=3000, locks=None, frozen=(), log_every=500, root_nodes=None, quiet=False):
    global _RE_CACHE; _RE_CACHE = {}
    root, nodes = root_nodes if root_nodes else build()
    for n in nodes:
        n.reg = np.zeros((169, len(n.acts))); n.ssum = np.zeros((169, len(n.acts)))
        n.lock = locks.get(n.name) if locks else None
    r0 = np.ones((6, 169)); hist = []
    t0 = time.time()
    for it in range(1, iters + 1):
        cfr(root, r0, P, it, frozen)
        if it % log_every == 0 or it == iters:
            ex = exploitability(root, P); g = sum(v['gain'] for v in ex.values())
            hist.append((it, g)); 
            if not quiet: print(f'it {it}  NashConv {g*1000:.2f} mbb/hand  ({time.time()-t0:.0f}s)', flush=True)
    return root, nodes, hist

def reach_freq(root):
    """frequency (combo-weighted, given node reached) of each action per node + the reach vector of acting seat"""
    out = {}
    def rec(n, r):
        if n.kind != 'dec': return
        p = n.seat; sg = avg(n); rp = r[p]
        wsum = (W * rp).sum()
        fr = {a: float((W * rp * sg[:, k]).sum() / wsum) if wsum > 0 else 0 for k, a in enumerate(n.acts)}
        out[n.name] = dict(seat=SEATS[p], acts=n.acts, freq=fr, reach_range=rp.copy(), strat=sg.copy())
        for k, ch in enumerate(n.kids):
            rr = r.copy(); rr[p] = r[p] * sg[:, k]; rec(ch, rr)
    rec(root, np.ones((6, 169)))
    return out

def dump(root, path, meta):
    rf = reach_freq(root); js = {'meta': meta, 'names': NAMES, 'nodes': {}}
    for k, v in rf.items():
        js['nodes'][k] = dict(seat=v['seat'], acts=v['acts'], freq={a: round(x, 4) for a, x in v['freq'].items()},
                              strat=[[round(float(x), 3) for x in row] for row in v['strat']],
                              reach=[round(float(x), 3) for x in v['reach_range']])
    json.dump(js, open(path, 'w'), separators=(',', ':'))
    return rf

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--iters', type=int, default=3000); ap.add_argument('--norake', action='store_true')
    ap.add_argument('--out', default=None); ap.add_argument('--spread', type=float, default=1.6); a = ap.parse_args()
    P = default_params(); P['rake'] = not a.norake; P['spread'] = a.spread
    root, nodes, hist = solve(P, a.iters)
    print('nodes', len(nodes))
    rf = dump(root, a.out or os.path.join(HERE, 'gto_%s.json' % ('norake' if a.norake else 'rake')), dict(params=P, iters=a.iters, hist=hist))
    for k in ['UTGrfi', 'HJrfi', 'COrfi', 'BTNrfi', 'SBrfi']: print(k, {a: round(100 * x, 1) for a, x in rf[k]['freq'].items()})
    for op in ['UTG', 'HJ', 'CO', 'BTN', 'SB']:
        k = op + 'open>BB'; print(k, {a: round(100 * x, 1) for a, x in rf[k]['freq'].items()})
