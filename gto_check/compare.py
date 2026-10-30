#!/usr/bin/env python3
"""GTO-vs-pool significance check for every exploit rule in the 4 preview tabs (3bet / iso / lines / reads).
Inputs: data/gto_flops.pkl (gto_post.py), data/pool_counts.json (pool_post.py), read_v1 reads.json,
lines_v1 rules.json, exploit_v3 solve_3bet.json + preflop GTO, pages_v1_postflop exp EVs, pool_stats.json.
Verdict: 'sig' = 95% CI of (pool - GTO) excludes 0 AND EV gain >= 0.05bb per occurrence;
'marg' = CI excludes 0 but EV < 0.05 (or EV ok but CI touches 0); 'ns' = neither; 'nonode' = no solver node."""
import os, sys, re, json, pickle, gzip, glob, math
import numpy as np
from collections import defaultdict
os.nice(19)
HERE = os.path.dirname(os.path.abspath(__file__)); D = HERE + '/data'
PS = '/workspace/outputs/poker_solver'
rng = np.random.default_rng(7)
GF = pickle.load(open(D + '/gto_flops.pkl', 'rb'))['data']
PC = json.load(open(D + '/pool_counts.json'))
SPT = {'SRP': ['BTN_BB', 'CO_BB', 'HJ_BB', 'UTG_BB'], '3BP': ['SB3_BTN', 'BB3_BTN']}
# SRP spot weights = pool share of opener seat (heads-up SRP vs BB)
HU = None
def spot_weights():
    import pickle as pk
    R = pk.load(open(PS + '/read_v1/data/hu.pkl', 'rb')); c = defaultdict(int)
    for r in R:
        if r['t'] == 'SRP' and r['pc'] == 'BB' and r['ip'] == 'A' and r['stk'] >= 40 and r['pa'] in ('UTG', 'HJ', 'CO', 'BTN'): c[r['pa'] + '_BB'] += 1
        if r['t'] == '3BP' and r['ip'] == 'C' and r['pa'] in ('SB', 'BB') and r['stk'] >= 40: c[r['pa'] + '3_BTN'] += 1
    return dict(c)
SW = spot_weights()
GRP = 'SMWDA'
def keys_match(sptype, pl, pat):
    rx = re.compile(pat); out = set()
    for sp in SPT[sptype]:
        for fl, d in GF[sp].items():
            for (p, l) in d:
                if p == pl and rx.fullmatch(l): out.add(l)
    return sorted(out)
def gto_stat(sptype, pl, pat, num, den=None, grp=None, nb=400):
    """num: acts in numerator. den: acts in denominator (None = all mass at node).
    grp: if set, composition = share of groups `grp` within mass of acts `num` (den ignored)."""
    ks = keys_match(sptype, pl, pat)
    per = []  # (spot, flop, numer, denom)
    for sp in SPT[sptype]:
        for fl, d in GF[sp].items():
            nu = de = 0.0
            for l in ks:
                e = d.get((pl, l))
                if not e: continue
                if grp is None:
                    nu += sum(e['a'].get(a, 0) for a in num)
                    de += e['m'] if den is None else sum(e['a'].get(a, 0) for a in den)
                else:
                    for a in num:
                        g = e['g'].get(a, {}); de += sum(g.values()); nu += sum(g.get(x, 0) for x in grp)
            per.append((sp, nu, de))
    if not per or sum(p[2] for p in per) <= 0: return None
    def est(rows):
        tot = 0.0
        for sp in SPT[sptype]:
            r = [x for x in rows if x[0] == sp]; de = sum(x[2] for x in r)
            if de <= 0: continue
            tot += SW.get(sp, 1) * sum(x[1] for x in r) / de
        ws = sum(SW.get(sp, 1) for sp in SPT[sptype] if sum(x[2] for x in rows if x[0] == sp) > 0)
        return tot / ws
    v = est(per); bs = []
    bysp = {sp: [x for x in per if x[0] == sp] for sp in SPT[sptype]}
    for _ in range(nb):
        rows = []
        for sp, r in bysp.items():
            if r: rows += [r[i] for i in rng.integers(0, len(r), len(r))]
        bs.append(est(rows))
    return dict(v=v, se=float(np.std(bs)), keys=ks, nflops=len(per))
def pool_freq(sptype, pl, pat, num, den=None, table='cntl'):
    T = PC[table][sptype]; rx = re.compile(pat); k = n = 0
    for key, c in T.items():
        p, l = key.split('|', 1)
        if p != pl or not rx.fullmatch(l): continue
        k += sum(c.get(a, 0) for a in num); n += sum(c.values()) if den is None else sum(c.get(a, 0) for a in den)
    if n == 0: return None
    p = k / n; return dict(v=p, se=math.sqrt(max(p * (1 - p), 1e-6) / n), n=n)
def diff(pool, gto):
    if not pool or not gto: return None
    d = pool['v'] - gto['v']; se = math.sqrt(pool['se'] ** 2 + gto['se'] ** 2)
    return dict(d=d, lo=d - 1.96 * se, hi=d + 1.96 * se, sig=(d - 1.96 * se > 0 or d + 1.96 * se < 0))
def verdict(df, ev):
    if df is None: return 'nonode'
    big = ev is not None and ev >= 0.05
    if df['sig'] and big: return 'sig'
    if df['sig'] or big: return 'marg'
    return 'ns'
R3 = lambda x: None if x is None else round(x, 3)
# ------------------------------------------------------------------ frequency claims (postflop)
FB = 'bS|bB'
CLAIMS = {
 'srp_fold_cbS': ('SRP', 'OOP', r'x bS', ['f'], None, 'BB 面對 c-bet 33% 棄牌', 5.5),
 'srp_fold_cbB': ('SRP', 'OOP', r'x bB', ['f'], None, 'BB 面對 c-bet 75% 棄牌', 5.5),
 'srp_xr': ('SRP', 'OOP', r'x b[SB]', ['r'], None, 'BB 翻牌過牌加注', 5.5),
 'srp_cbet': ('SRP', 'IP', r'x', ['bS', 'bB', 'bO'], None, '開池者翻牌 c-bet', 5.5),
 'srp_fold_tS': ('SRP', 'OOP', r'x b[SB] c/x bS', ['f'], None, 'BB 轉牌面對半池棄牌', 10),
 'srp_fold_tB': ('SRP', 'OOP', r'x b[SB] c/x bB', ['f'], None, 'BB 轉牌面對 1 池棄牌', 10),
 'srp_tbarrel': ('SRP', 'IP', r'x b[SB] c/x', ['bS', 'bB', 'bO'], None, '開池者轉牌續打', 10),
 'srp_fold_delay': ('SRP', 'OOP', r'x x/x b[SB]', ['f'], None, 'BB 面對延遲 c-bet 棄牌', 5.5),
 'srp_fold_rS': ('SRP', 'OOP', r'x b[SB] c/x b[SB] c/x bS', ['f'], None, 'BB 河牌面對半池棄牌', 18),
 'srp_fold_rB': ('SRP', 'OOP', r'x b[SB] c/x b[SB] c/x bB', ['f'], None, 'BB 河牌面對 1 池棄牌', 18),
 'srp_fold_rstab': ('SRP', 'OOP', r'x x/x x/x b[BO]', ['f'], None, 'BB 翻轉都過後河牌面對大注棄牌', 5.5),
 'srp_fold_probe': ('SRP', 'IP', r'x x/b[SB]', ['f'], None, '開池者面對轉牌探測棄牌', 5.5),
 'srp_probe': ('SRP', 'OOP', r'x x/', ['bS', 'bB', 'bO'], None, 'BB 轉牌探測下注', 5.5),
 'srp_fold_rlead': ('SRP', 'IP', r'x x/x x/b[SBO]', ['f'], None, '翻轉都過、BB 河牌下注時開池者棄牌', 5.5),
 '3bp_fold_cbS': ('3BP', 'IP', r'bS', ['f'], None, '3bet 底池面對 c-bet 33% 棄牌', 21),
 '3bp_fold_cbB': ('3BP', 'IP', r'bB', ['f'], None, '3bet 底池面對 c-bet 75% 棄牌', 21),
 '3bp_cbet': ('3BP', 'OOP', r'', ['bS', 'bB', 'bO'], None, '3bettor 翻牌 c-bet', 21),
 '3bp_fold_t': ('3BP', 'IP', r'b[SB] c/b[SB]', ['f'], None, '3bet 底池轉牌面對下注棄牌', 35),
 '3bp_fold_r': ('3BP', 'IP', r'b[SB] c/b[SB] c/b[SB]', ['f'], None, '3bet 底池河牌面對下注棄牌', 60),
}
BSZ = {'srp_fold_cbS': .33, 'srp_fold_cbB': .75, 'srp_xr': 1.0, 'srp_cbet': .5, 'srp_fold_tS': .5, 'srp_fold_tB': 1.0, 'srp_tbarrel': .7,
       'srp_fold_delay': .6, 'srp_fold_rS': .5, 'srp_fold_rB': 1.0, 'srp_fold_rstab': 1.0, 'srp_fold_probe': .66, 'srp_probe': .66,
       'srp_fold_rlead': .75, '3bp_fold_cbS': .33, '3bp_fold_cbB': .75, '3bp_cbet': .5, '3bp_fold_t': .75, '3bp_fold_r': .75}
def run_claim(cid):
    sp, pl, pat, num, den, zh, pot = CLAIMS[cid]
    tab = 'cnt' if any(a.startswith('b') for a in num) else 'cntl'
    g = gto_stat(sp, pl, pat, num, den); p = pool_freq(sp, pl, pat, num, den, tab)
    df = diff(p, g)
    return dict(id=cid, zh=zh, gto=R3(g and g['v']), gto_se=R3(g and g['se']), pool=R3(p and p['v']), n=p and p['n'],
                d=R3(df and df['d']), lo=R3(df and df['lo']), hi=R3(df and df['hi']), ci_sig=bool(df and df['sig']), nflops=g and g['nflops'], pot=pot,
                ev_dev=R3(df and abs(df['d']) * (1 + BSZ[cid]) * pot), kind='fold' if num == ['f'] else 'freq')
FREQ = {c: run_claim(c) for c in CLAIMS}
print('freq claims'); [print(f"  {c:16s} GTO {v['gto']} pool {v['pool']} n={v['n']} d={v['d']} [{v['lo']},{v['hi']}] {'*' if v['ci_sig'] else ''}") for c, v in FREQ.items()]
# ------------------------------------------------------------------ reads (range composition / response)
READS = {r['id']: r for r in json.load(open(PS + '/read_v1/data/reads.json'))}
# id: (sptype, villain pl, villain pat, villain acts, hero pl, hero pat, stat, pot_bb)
RMAP = {
 'ip_xr_big': ('SRP', 'OOP', r'x b[SB]', ['r'], 'IP', r'x b[SB] r', 'S', 5.5),
 'ip_probe': ('SRP', 'OOP', r'x x/', ['bS', 'bB', 'bO'], 'IP', r'x x/b[SBO]', 'A', 5.5),
 'ip_turn_xr': ('SRP', 'OOP', r'x b[SB] c/x b[SB]', ['r'], 'IP', r'x b[SB] c/x b[SB] r', 'S', 10),
 'ip_riv_small': ('SRP', 'OOP', r'(x b[SB] c/x x|x x/x x)/', ['bS'], 'IP', r'(x b[SB] c/x x|x x/x x)/bS', 'A', 12),
 'ip_riv_big': ('SRP', 'OOP', r'(x b[SB] c/x x|x x/x x)/', ['bB'], 'IP', r'(x b[SB] c/x x|x x/x x)/bB', 'S', 12),
 'ip_riv_over': ('SRP', 'OOP', r'(x b[SB] c/x x|x x/x x)/', ['bO'], 'IP', r'(x b[SB] c/x x|x x/x x)/bO', 'S', 12),
 'bb_cb_small': ('SRP', 'IP', r'x', ['bS'], 'OOP', r'x bS', 'A', 5.5),
 'bb_cb_big': ('SRP', 'IP', r'x', ['bB'], 'OOP', r'x bB', 'A', 5.5),
 'bb_delay': ('SRP', 'IP', r'x x/x', ['bS', 'bB', 'bO'], 'OOP', r'x x/x b[SBO]', 'A', 5.5),
 'bb_barrel2': ('SRP', 'IP', r'x b[SB] c/x', ['bS', 'bB', 'bO'], 'OOP', r'x b[SB] c/x b[SBO]', 'A', 10),
 'bb_barrel3': ('SRP', 'IP', r'x b[SB] c/x b[SB] c/x', ['bB'], 'OOP', r'x b[SB] c/x b[SB] c/x bB', 'S', 18),
 '3b_raised': ('3BP', 'IP', r'b[SB]', ['r'], 'OOP', r'b[SB] r', 'S', 21),
 '3c_cbet': ('3BP', 'OOP', r'', ['bS', 'bB'], 'IP', r'b[SB]', 'A', 21),
 # decision reads: villain fold rate vs HW's bet (pool resp vs GTO fold); hero node = HW's betting node
 'ip_turn_dec': ('SRP', 'OOP', r'x b[SB] c/x bS', ['f'], 'IP', r'x b[SB] c/x', 'F', 10),
 'ip_riv_dec': ('SRP', 'OOP', r'x b[SB] c/x b[SB] c/x bS', ['f'], 'IP', r'x b[SB] c/x b[SB] c/x', 'F', 18),
 'bb_probe': ('SRP', 'IP', r'x x/bS', ['f'], 'OOP', r'x x/', 'F', 5.5),
 '3b_riv_dec': ('3BP', 'IP', r'b[SB] c/b[SB] c/bS', ['f'], 'OOP', r'b[SB] c/b[SB] c/', 'F', 60),
}
NONODE = {'ip_donk': 'GTO 樹沒有 BB 翻牌領先下注（GTO 幾乎不 donk）', 'ip_xr_min': '解算器只有 3x 加注，沒有最小加注節點',
          'ip_xc_lead': '解算器轉牌 BB 不領先（翻牌跟注後）', 'bb_donk_raised': '解算器沒有 BB donk 節點',
          '3c_over': '解算器翻牌沒有超池下注', 'iso_donk': '沒有跛入底池的 GTO 解', 'iso_xc_lead': '沒有跛入底池的 GTO 解',
          'iso_xr': '沒有跛入底池的 GTO 解', 'iso_turn_dec': '沒有跛入底池的 GTO 解'}
def pool_comp(r, stat):
    g = r['grp']; G = g.get('G', 0); wda = g.get('W', 0) + g.get('D', 0) + g.get('A', 0)
    if stat == 'S': v = g.get('S', 0)
    else: v = g.get('A', 0) + (G * g.get('A', 0) / wda if wda > 0 else 0)
    n = max(r.get('ess') or r.get('nsd') or 1, 1)
    return dict(v=v, se=math.sqrt(max(v * (1 - v), 1e-6) / n), n=n)
def hero_gto_cont(sp, pl, pat, cont_acts):
    """GTO hero continue/bet prob by group at hero node + group share of hero range."""
    ks = keys_match(sp, pl, pat); m = defaultdict(float); c = defaultdict(float)
    for s in SPT[sp]:
        for fl, d in GF[s].items():
            for l in ks:
                e = d.get((pl, l))
                if not e: continue
                for a, gg in e['g'].items():
                    for G, x in gg.items():
                        m[G] += x * SW.get(s, 1) / max(len(GF[s]), 1)
                        if a in cont_acts: c[G] += x * SW.get(s, 1) / max(len(GF[s]), 1)
    tot = sum(m.values())
    return {G: (c[G] / m[G] if m[G] > 0 else None) for G in GRP}, {G: m[G] / tot if tot else 0 for G in GRP}
RX = {'ip_xr_big': 1.0, 'ip_probe': .66, 'ip_turn_xr': 1.0, 'ip_riv_small': .5, 'ip_riv_big': 1.0, 'ip_riv_over': 1.5, 'bb_cb_small': .33,
      'bb_cb_big': .75, 'bb_delay': .6, 'bb_barrel2': .7, 'bb_barrel3': 1.0, '3b_raised': 1.0, '3c_cbet': .5,
      'ip_turn_dec': .6, 'ip_riv_dec': .6, 'bb_probe': .6, '3b_riv_dec': .6}
READ_OUT = {}
for rid, r in READS.items():
    if rid in NONODE:
        READ_OUT[rid] = dict(id=rid, verdict='nonode', note=NONODE[rid]); continue
    sp, vpl, vpat, vacts, hpl, hpat, stat, pot = RMAP[rid]
    if stat == 'F':
        g = gto_stat(sp, vpl, vpat, vacts); p = pool_freq(sp, vpl, vpat, vacts, None, 'cntl')
        if p is None or p['n'] < 30:
            rs = r.get('resp') or {}; pv = rs.get('fold'); n = rs.get('n') or 1
            p = dict(v=pv, se=math.sqrt(pv * (1 - pv) / n), n=n)
        bet = [a for a in ('bS', 'bB', 'bO')]
        cont, share = hero_gto_cont(sp, hpl, hpat, bet)
        gains_dir = {}
        for G in GRP:
            if cont.get(G) is None or G not in r['act']: continue
            ex = 1.0 if r['act'].get(G, '').startswith('下注') else 0.0
            gains_dir[G] = ex - cont[G]
    else:
        g = gto_stat(sp, vpl, vpat, vacts, grp=[stat] if stat == 'S' else ['A']); p = pool_comp(r, stat)
        cont, share = hero_gto_cont(sp, hpl, hpat, ['c', 'r'])
        gains_dir = {}
        for G in GRP:
            a = r['act'].get(G, '')
            if cont.get(G) is None or G not in r['act']: continue
            ex = 0.5 if '邊緣' in a else (1.0 if ('跟' in a or '加注' in a) else 0.0)
            gains_dir[G] = ex - cont[G]
    df = diff(p, g)
    loose = sum(share.get(G, 0) * (gains_dir.get(G, 0)) for G in GRP)
    x = RX[rid]; k = (1 + x) if stat == 'F' else (1 + 2 * x)
    ev = abs(df['d']) * k * pot if df else None
    # direction the read relies on: looser (more calls / more bets) needs weaker villain range (S down / A up) or more folds (F up)
    need = (1 if loose > 0 else -1) * (-1 if stat == 'S' else 1)
    dir_ok = df is not None and (df['d'] * need > 0)
    READ_OUT[rid] = dict(id=rid, stat={'S': '兩對以上占比', 'A': '空氣占比', 'F': '對手棄牌率'}[stat], gto=R3(g and g['v']), gto_se=R3(g and g['se']),
                         pool=R3(p['v']), n=p['n'], d=R3(df and df['d']), lo=R3(df and df['lo']), hi=R3(df and df['hi']),
                         ev_bb=R3(ev), loose=R3(loose), dir_ok=bool(dir_ok), gto_cont={G: R3(x) for G, x in cont.items()},
                         verdict=(verdict(df, ev) if dir_ok else ('ns_dir' if df and df['sig'] else 'ns')))
print('reads'); [print(f"  {k:13s} {v.get('stat','')} GTO {v.get('gto')} pool {v.get('pool')} d={v.get('d')} [{v.get('lo')},{v.get('hi')}] EV {v.get('ev_bb')} loose {v.get('loose')} -> {v['verdict']}") for k, v in READ_OUT.items()]
json.dump(dict(freq=FREQ, reads=READ_OUT, sw=SW), open(D + '/stage1.json', 'w'), ensure_ascii=False, indent=1)
# ================================================================== stage 2: per-rule verdicts
def lvl(p): return None if p is None else (1.0 if p >= 0.65 else 0.0 if p <= 0.35 else 0.5)
def rd_ex(kind, a):
    if kind == 'dec': return 1.0 if a.startswith('下注') else 0.0
    return 0.5 if '邊緣' in a else (1.0 if ('跟' in a or '加注' in a) else 0.0)
def gto_act_zh(kind, G, p):
    l = lvl(p)
    if kind == 'dec': return {1.0: '下注', 0.0: '過牌', 0.5: '邊緣（GTO 混合）'}[l]
    return {1.0: '跟注', 0.0: '棄牌', 0.5: '邊緣'}[l]
RULES_READ = []
for rid, r in READS.items():
    o = READ_OUT[rid]
    for G, a in r['act'].items():
        e = dict(tab='rd', read=rid, grp=G, act=a)
        if o['verdict'] == 'nonode':
            e.update(v='nonode', note=o['note']); RULES_READ.append(e); continue
        p = o['gto_cont'].get(G); ex = rd_ex(r['kind'], a)
        e.update(gto_p=p, gto_act=gto_act_zh(r['kind'], G, p) if p is not None else None)
        if p is None or abs(ex - p) < 0.35:
            e['v'] = 'gto'; RULES_READ.append(e); continue
        loose = ex - p
        need = (1 if loose > 0 else -1) * (-1 if o['stat'] == '兩對以上占比' else 1)
        d = o['d']; sigci = (o['lo'] > 0 or o['hi'] < 0)
        ok = d * need > 0
        e['v'] = ('sig' if (ok and sigci and o['ev_bb'] >= 0.05) else 'marg' if ok and sigci else 'ns_dir' if (sigci and not ok) else 'ns')
        RULES_READ.append(e)
LR = json.load(open(PS + '/lines_v1/data/rules.json'))
ORD = {'x': 0, 'small': 1, 'big': 2, 'f': 0, 'c': 1, 'r': 2}
BETCL = {('SRP_IP', 'f_cbet'): ('srp_fold_cbS', 'srp_fold_cbB'), ('SRP_IP', 'barrel'): ('srp_fold_tS', 'srp_fold_tB'),
         ('SRP_IP', 'delay'): ('srp_fold_delay',) * 2, ('SRP_IP', 'r_barrel'): ('srp_fold_rS', 'srp_fold_rB'),
         ('SRP_IP', 'r_stab'): ('srp_fold_rstab',) * 2, ('SRP_BB', 'probe'): ('srp_fold_probe',) * 2,
         ('SRP_BB', 'r_stab'): ('srp_fold_rlead',) * 2, ('3BP_3bettor', 'f_cbet'): ('3bp_fold_cbS', '3bp_fold_cbB'),
         ('3BP_3bettor', 'barrel'): ('3bp_fold_t',) * 2, ('3BP_3bettor', 'r_barrel'): ('3bp_fold_r',) * 2}
FACECL = {('SRP_IP', 'vs_probe'): 'ip_probe', ('SRP_IP', 'r_vs_bet'): 'ip_riv_small', ('SRP_BB', 'f_vs_cbet'): 'bb_cb_small',
          ('SRP_BB', 'vs_barrel'): 'bb_barrel2', ('SRP_BB', 'r_vs_bet'): 'bb_barrel3', ('3BP_caller', 'f_vs_cbet'): '3c_cbet',
          ('3BP_caller', 'vs_barrel'): None, ('3BP_caller', 'r_vs_bet'): None}
VALUE = ('strong', 'top_good')
RULES_LN = []
for r in LR:
    e = dict(tab='ln', id=r['id'], group=r['group'], cat=r['cat'], hc=r['hc'], ans=r['ans'], gto=r['gto'])
    gf = r.get('gto_f') or {}
    e['gto_p'] = R3(gf.get(r['ans'])); e['gto_main'] = R3(gf.get(r['gto']))
    delta = ORD[r['ans']] - ORD[r['gto']]; key = (r['group'], r['cat'])
    if key in BETCL:
        hi = r['ans'] if ORD[r['ans']] > ORD[r['gto']] else r['gto']
        cid = BETCL[key][1 if hi == 'big' else 0]; c = FREQ[cid]
        need = (1 if delta > 0 else -1) * (-1 if r['hc'] in VALUE else 1)
        if r['hc'] in VALUE and delta < 0 and hi == 'big' and r['ans'] == 'small': need = 1  # value small instead of big: pool over-folds to big
        d, lo, hi_, ev = c['d'], c['lo'], c['hi'], c['ev_dev']
        e.update(claim=cid, claim_zh=c['zh'], pool=c['pool'], gto_ref=c['gto'])
    elif key == ('SRP_IP', 'vs_raise'):
        cid = 'ip_xr_big' if r['street'] == 'flop' else 'ip_turn_xr'; c = READ_OUT[cid]
        need = (1 if delta > 0 else -1) * -1; d, lo, hi_, ev = c['d'], c['lo'], c['hi'], c['ev_bb']
        e.update(claim=cid, claim_zh=c['stat'], pool=c['pool'], gto_ref=c['gto'])
    elif FACECL.get(key):
        cid = FACECL[key]; c = READ_OUT[cid]
        need = (1 if delta > 0 else -1) * (-1 if c['stat'] == '兩對以上占比' else 1); d, lo, hi_, ev = c['d'], c['lo'], c['hi'], c['ev_bb']
        e.update(claim=cid, claim_zh=c['stat'], pool=c['pool'], gto_ref=c['gto'])
    else:
        e['v'] = 'gto' if not r['dev'] else 'nonode'; RULES_LN.append(e); continue
    if not r['dev']:
        e['v'] = 'gto'; RULES_LN.append(e); continue
    sigci = lo > 0 or hi_ < 0; ok = d * need > 0
    e['v'] = ('sig' if (ok and sigci and ev >= 0.05) else 'marg' if ok and sigci else 'ns_dir' if (sigci and not ok) else 'ns')
    e['d'] = d; e['lo'] = lo; e['hi'] = hi_; e['ev'] = ev
    RULES_LN.append(e)
# ---- 3bet tab
sys.path.insert(0, PS + '/rfi_audit'); sys.path.insert(0, PS + '/preflop')
import audit as AU
PSTAT = json.load(open('/workspace/poker/hhdealer/pool_stats.json'))['NL2']['preflop']
LD_PATH = '/workspace/poker_mb/preview_3bet_iso_lines/site/learn_data.js'
_s = open(LD_PATH).read(); LD = json.loads(_s[_s.index('{'):_s.rindex('}') + 1])
NAMES = AU.NAMES; WC = np.array([6 if len(n) == 2 else 4 if n[2] == 's' else 12 for n in NAMES], float)
RULES_TB = []
for key, t in (LD['tb'].items() if isinstance(LD['tb'], dict) else enumerate(LD['tb'])):
    o, h = t['o'], t['h']; gn = AU.G['nodes'].get(f'{o}open>{h}3b'); hn = AU.G['nodes'].get(f'{o}open>{h}')
    f3 = PSTAT[o]['f3']; n = f3['n']; pf = f3['fold'] / 100; p4 = f3['raise'] / 100
    gfold = gn['freq']['fold'] if gn else None; g4 = gn['freq'].get('4bet') if gn else None
    st = np.array(hn['strat']) if hn else None
    g3 = float((st[:, hn['acts'].index('3bet')] * WC).sum() / WC.sum()) if hn else None
    ex3 = (t['pct']['value'] + t['pct']['bluff']) / 100
    se = math.sqrt(pf * (1 - pf) / n); d = pf - gfold if gfold is not None else None
    lo, hi_ = (d - 1.96 * se, d + 1.96 * se) if d is not None else (None, None)
    risk = t['to'] - (1 if h == 'BB' else 0.5 if h == 'SB' else 0); potw = t['open'] + 1.5
    ev = abs(d) * (potw + risk) * abs(ex3 - g3) / max(ex3 + g3, 1e-6) * 2 if d is not None else None  # per 3-bet-opportunity scaled by range change share
    evh = abs(d) * (potw + risk) if d is not None else None   # per bluff 3-bet
    need = 1 if ex3 > g3 else -1
    se4 = math.sqrt(p4 * (1 - p4) / n); d4 = p4 - g4 if g4 is not None else 0
    sig4 = abs(d4) > 1.96 * math.sqrt(se4 ** 2)
    sigci = d is not None and (lo > 0 or hi_ < 0); ok = d is not None and d * need > 0
    if need > 0 and not (ok and sigci) and d4 < 0 and sig4:   # looser 3-bets justified by a 4-bet deficit instead
        ok, sigci, evh = True, True, abs(d4) * risk
    v = 'sig' if (ok and sigci and evh >= 0.05) else 'marg' if ok and sigci else 'ns_dir' if sigci and not ok else 'ns'
    RULES_TB.append(dict(tab='tb', id=f'{o}>{h}', pool_f3=round(pf, 3), gto_f3=R3(gfold), n=n, d=R3(d), lo=R3(lo), hi=R3(hi_), pool_4b=round(p4, 3), gto_4b=R3(g4),
                         ex3=round(ex3, 3), gto3=R3(g3), ev_per_bluff=R3(evh), v=v))
RULES_ISO = []
for t in (LD['iso'].values() if isinstance(LD['iso'], dict) else LD['iso']):
    RULES_ISO.append(dict(tab='iso', id=f"{t['l']}>{t['h']}", v='nonode', note='GTO 不跛入，沒有跛入底池的理論節點', pool_lf=t['lf'] / 100))
ALL = RULES_TB + RULES_ISO + RULES_LN + RULES_READ
from collections import Counter
summ = {tab: dict(Counter(e['v'] for e in ALL if e['tab'] == tab)) for tab in ('tb', 'iso', 'ln', 'rd')}
summ['all'] = dict(Counter(e['v'] for e in ALL))
print('summary', json.dumps(summ, ensure_ascii=False))
for e in RULES_TB: print(' tb', e)
json.dump(dict(freq=FREQ, reads=READ_OUT, sw=SW, rules=ALL, summary=summ), open(D + '/gto_check.json', 'w'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
