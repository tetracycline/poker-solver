"""NL2 pool postflop lock targets (pool_stats.json, 2,334,487 hands, HU pots only).
Frequencies are what the pool DOES (observable for every hand); WHICH combos take each action is unknown
(cards only seen at showdown) -> combos are assigned by the solver's own ordering (driver make_lock)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, math, re
PS = json.load(open(f'{ROOTDIR}/inputs/pool_stats.json'))['NL2']
PH = PS['postflop_HU']; MIN_N = 500
def tex(flop):
    r = [c[0] for c in (flop[0:2], flop[2:4], flop[4:6])]; s = [flop[1], flop[3], flop[5]]
    ns = len(set(s)); suit = 'mono' if ns == 1 else 'twotone' if ns == 2 else 'rainbow'
    paired = 'paired' if len(set(r)) < 3 else 'unpaired'
    hi = max('23456789TJQKA'.index(x) for x in r); h = 'A高' if hi == 12 else 'K/Q高' if hi >= 10 else 'J/T高' if hi >= 8 else '9以下'
    return suit, paired, h
def bucket(lbl):
    if lbl == 'a': return '>110%'
    p = int(lbl[1:])
    return '≤33%' if p <= 33 else '34-55%' if p <= 55 else '56-80%' if p <= 80 else '81-110%' if p <= 110 else '>110%'
def wilson(p, n, z=1.96):
    if not n: return (0, 1)
    d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return ((c - r) / d, (c + r) / d)
MID = {'≤33%': 25, '34-55%': 45, '56-80%': 68, '81-110%': 95, '>110%': 150}
def SZ(dist):  # pool bet-size distribution -> [(bucket midpoint % pot, share)]; driver maps to nearest tree size
    return [[MID[k], v / 100] for k, v in dist.items()]
def resp(d):  # fold/raise dict from pool entry
    return dict(fold=d['fold'] / 100, raise_=d['raise'] / 100, n=d['n'])
def build(spot_kind, pfr, villain_is_pfr, flop):
    """returns list of (pattern, target dict, n, source) for the villain's nodes"""
    K = spot_kind; P = 'IP' if pfr == 'ip' else 'OOP'; base = PH[f'{K}_PFR_{P}']
    out = []
    def add(pat, n, src, **t):
        if n >= MIN_N: out.append(dict(pat=pat, n=n, src=src, **t))
    suit, paired, hi = tex(flop); tk = f'{P}|{suit}|{paired}|{hi}'
    if pfr == 'ip':
        if not villain_is_pfr:   # villain = OOP caller
            # flop facing c-bet, per size, texture-adjusted (SRP only)
            adj_f = adj_r = 0.0; tsrc = ''
            if K == 'SRP' and tk in PS['fold_to_cbet_by_texture_SRP'] and PS['fold_to_cbet_by_texture_SRP'][tk]['n'] >= MIN_N:
                t = PS['fold_to_cbet_by_texture_SRP'][tk]; adj_f = t['fold'] / 100 - base['vs_cbet']['fold'] / 100; adj_r = t['raise'] / 100 - base['vs_cbet']['raise'] / 100; tsrc = f' + texture {tk} (n={t["n"]})'
            for lbl in ('b33', 'b75'):
                d = base['vs_cbet_by_size'][bucket(lbl)]
                add(f'^x {lbl}$', d['n'], f'{K}_PFR_{P}.vs_cbet_by_size[{bucket(lbl)}]{tsrc}', fold=min(.95, max(.02, d['fold'] / 100 + adj_f)), raise_=min(.5, max(0.005, d['raise'] / 100 + adj_r)))
            for lbl in ('b66', 'b50', 'b100'):
                d = base['vs_turn_barrel_by_size'][bucket(lbl)]
                add(f'^x b\\d+ c/x {lbl}$', d['n'], f'{K}_PFR_{P}.vs_turn_barrel_by_size[{bucket(lbl)}]', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            d = PH[f'{K}_probe']; add('^x x/$', d['n'], f'{K}_probe', bet=d['pct'] / 100, sizes=SZ(PH[f'{K}_donk']['sizes']), szsrc=f'{K}_donk.sizes (proxy)')
            d = base['vs_delayed_cbet']; add('^x x/x b\\d+$', d['n'], f'{K}_PFR_{P}.vs_delayed_cbet', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            for lbl in ('b75', 'b50', 'b100', 'a'):
                d = base['vs_river_barrel_by_size'][bucket(lbl)]
                add(f'^x b\\d+ c/x b\\d+ c/x {lbl}$', d['n'], f'{K}_PFR_{P}.vs_river_barrel_by_size[{bucket(lbl)}]', fold=d['fold'] / 100, raise_=d['raise'] / 100)
        else:  # villain = IP PFR
            cb = base['cbet']['pct'] / 100; n = base['cbet']['n']; src = f'{K}_PFR_{P}.cbet'
            if K == 'SRP' and tk in PS['cbet_by_texture_SRP'] and PS['cbet_by_texture_SRP'][tk]['n'] >= MIN_N:
                t = PS['cbet_by_texture_SRP'][tk]; cb, n, src = t['cbet'] / 100, t['n'], f'cbet_by_texture_SRP[{tk}]'
            add('^x$', n, src, bet=cb, sizes=SZ(base['cbet_size']), szsrc=f'{K}_PFR_{P}.cbet_size')
            d = base['vs_cbet_raise_resp']; add('^x b\\d+ r$', d['n'], f'{K}_PFR_{P}.vs_cbet_raise_resp', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            d = base['turn_barrel']; add('^x b\\d+ c/x$', d['n'], f'{K}_PFR_{P}.turn_barrel', bet=d['pct'] / 100, sizes=SZ(base['turn_barrel_size']), szsrc=f'{K}_PFR_{P}.turn_barrel_size')
            d = base['delayed_cbet']; add('^x x/x$', d['n'], f'{K}_PFR_{P}.delayed_cbet', bet=d['pct'] / 100, sizes=SZ(base['turn_barrel_size']), szsrc=f'{K}_PFR_{P}.turn_barrel_size (proxy)')
            d = base['vs_probe']; add('^x x/b\\d+$', d['n'], f'{K}_PFR_{P}.vs_probe', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            d = base['river_barrel']; add('^x b\\d+ c/x b\\d+ c/x$', d['n'], f'{K}_PFR_{P}.river_barrel', bet=d['pct'] / 100, sizes=SZ(base['river_barrel_size']), szsrc=f'{K}_PFR_{P}.river_barrel_size')
    else:
        if not villain_is_pfr:   # villain = IP caller vs OOP PFR
            adj_f = adj_r = 0.0; tsrc = ''
            if K == 'SRP' and tk in PS['fold_to_cbet_by_texture_SRP'] and PS['fold_to_cbet_by_texture_SRP'][tk]['n'] >= MIN_N:
                t = PS['fold_to_cbet_by_texture_SRP'][tk]; adj_f = t['fold'] / 100 - base['vs_cbet']['fold'] / 100; adj_r = t['raise'] / 100 - base['vs_cbet']['raise'] / 100; tsrc = f' + texture {tk} (n={t["n"]})'
            for lbl in ('b33', 'b75'):
                d = base['vs_cbet_by_size'][bucket(lbl)]
                add(f'^{lbl}$', d['n'], f'{K}_PFR_{P}.vs_cbet_by_size[{bucket(lbl)}]{tsrc}', fold=min(.95, max(.02, d['fold'] / 100 + adj_f)), raise_=min(.5, max(0.005, d['raise'] / 100 + adj_r)))
            d = PH[f'{K}_float_bet_when_pfr_checks_oop']; add('^x$', d['n'], f'{K}_float_bet_when_pfr_checks_oop', bet=d['pct'] / 100, sizes=SZ(PH[f'{K}_donk']['sizes']), szsrc=f'{K}_donk.sizes (proxy)')
            for lbl in ('b66', 'b50', 'b100'):
                d = base['vs_turn_barrel_by_size'][bucket(lbl)]
                add(f'^b\\d+ c/{lbl}$', d['n'], f'{K}_PFR_{P}.vs_turn_barrel_by_size[{bucket(lbl)}]', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            d = PH[f'{K}_turn_stab_ip_after_pfr_checks']; add('^b\\d+ c/x$', d['n'], f'{K}_turn_stab_ip_after_pfr_checks', bet=d['pct'] / 100, sizes=SZ(PH[f'{K}_donk']['sizes']), szsrc=f'{K}_donk.sizes (proxy)')
            d = base['vs_delayed_cbet']; add('^x x/b\\d+$', d['n'], f'{K}_PFR_{P}.vs_delayed_cbet', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            for lbl in ('b75', 'b50', 'b100', 'a'):
                d = base['vs_river_barrel_by_size'][bucket(lbl)]
                add(f'^b\\d+ c/b\\d+ c/{lbl}$', d['n'], f'{K}_PFR_{P}.vs_river_barrel_by_size[{bucket(lbl)}]', fold=d['fold'] / 100, raise_=d['raise'] / 100)
        else:  # villain = OOP PFR
            cb = base['cbet']['pct'] / 100; n = base['cbet']['n']; src = f'{K}_PFR_{P}.cbet'
            if K == 'SRP' and tk in PS['cbet_by_texture_SRP'] and PS['cbet_by_texture_SRP'][tk]['n'] >= MIN_N:
                t = PS['cbet_by_texture_SRP'][tk]; cb, n, src = t['cbet'] / 100, t['n'], f'cbet_by_texture_SRP[{tk}]'
            add('^$', n, src, bet=cb, sizes=SZ(base['cbet_size']), szsrc=f'{K}_PFR_{P}.cbet_size')
            d = base['vs_cbet_raise_resp']; add('^b\\d+ r$', d['n'], f'{K}_PFR_{P}.vs_cbet_raise_resp', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            d = base['vs_ip_float_bet']; add('^x b\\d+$', d['n'], f'{K}_PFR_{P}.vs_ip_float_bet', fold=d['fold'] / 100, raise_=d['raise'] / 100)
            d = base['turn_barrel']; add('^b\\d+ c/$', d['n'], f'{K}_PFR_{P}.turn_barrel', bet=d['pct'] / 100, sizes=SZ(base['turn_barrel_size']), szsrc=f'{K}_PFR_{P}.turn_barrel_size')
            d = base['delayed_cbet']; add('^x x/$', d['n'], f'{K}_PFR_{P}.delayed_cbet', bet=d['pct'] / 100, sizes=SZ(base['turn_barrel_size']), szsrc=f'{K}_PFR_{P}.turn_barrel_size (proxy)')
            d = base['river_barrel']; add('^b\\d+ c/b\\d+ c/$', d['n'], f'{K}_PFR_{P}.river_barrel', bet=d['pct'] / 100, sizes=SZ(base['river_barrel_size']), szsrc=f'{K}_PFR_{P}.river_barrel_size')
    return out
def driver_locks(L):
    r = []
    for x in L:
        d = dict(pat=x['pat'])
        if 'bet' in x:
            d['bet'] = x['bet']
            if 'sizes' in x: d['sizes'] = x['sizes']
        else: d['fold'] = x['fold']; d['raise'] = x['raise_']
        r.append(d)
    return r
if __name__ == '__main__':
    for args in [('SRP', 'ip', False, 'Ks7d2c'), ('SRP', 'ip', True, 'Ks7d2c'), ('SRP', 'oop', False, 'Ks7d2c'), ('SRP', 'oop', True, 'Ks7d2c'), ('3BP', 'oop', False, 'Ks7d2c'), ('3BP', 'oop', True, 'Ks7d2c')]:
        L = build(*args); print(args, len(L))
        for x in L: print('   ', x)
