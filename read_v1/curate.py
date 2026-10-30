#!/usr/bin/env python3
"""Merge engine keys into curated reads, compute HW equity by hand group and best action. -> data/reads.json"""
import pickle, json, os, sys, random, re
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vclass import fine, GROUP, GROUP_ZH, FINE_ZH, texture, cards
from phevaluator import evaluate_cards
os.nice(19); random.seed(7)
R = pickle.load(open('data/hu.pkl', 'rb')); O = pickle.load(open('data/reads_raw.pkl', 'rb'))
DECK = [r + s for r in '23456789TJQKA' for s in 'shdc']
RK = '23456789TJQKA'
def pre(h):
    a, b = h[:2], h[2:]; x, y = RK.index(a[0]), RK.index(b[0])
    if x < y: x, y = y, x; a, b = b, a
    return RK[x] * 2 if x == y else RK[x] + RK[y] + ('s' if a[1] == b[1] else 'o')
SIZE = dict(VbS=(0.40,), VbB=(0.75,), VbO=(1.5,), Vrn=(0.55, 2.3), Vrg=(0.6, 3.2))
def need_of(tok):
    v = SIZE[tok]
    if len(v) == 1: x = v[0]; return x / (1 + 2 * x), x
    b, m = v; cost = (m - 1) * b; pot = 1 + b + m * b; return cost / (pot + cost), (b, m)
def merge(keys):
    ks = [k for k in keys if k in O]
    if not ks: return None
    N = sum(O[k]['n'] for k in ks); L = []; G = 0.0
    for k in ks:
        o = O[k]; f = o['n'] / N; G += f * o['grp'].get('G', 0)
        L += [(i, vh, w * f * (1 - o['grp'].get('G', 0))) for i, vh, w in o['leaves']]
    st = O[ks[0]]['street']; sw = sum(w for *_, w in L)
    ess = sw * sw / sum(w * w for *_, w in L)
    fc = Counter(); pc = Counter()
    for i, vh, w in L:
        c = fine(vh, R[i]['bd'][:4 + 2 * st]); fc[c] += w / sw * (1 - G); pc[pre(vh)] += w / sw * (1 - G)
    gs = Counter()
    for c, v in fc.items(): gs[GROUP[c]] += v
    gs['G'] = G
    return dict(keys=ks, n=N, nsd=len(L), ess=round(ess), street=st, G=G, L=L,
                grp={k: round(gs.get(k, 0), 3) for k in 'SMWDAG'}, fine={k: round(v, 3) for k, v in fc.most_common()},
                combos=[(h, round(v, 3)) for h, v in pc.most_common(10)])
def hw_eq(m, street, nleaf=1500, k=14):
    """equity of HW hand groups (classified at node street) vs merged range.
    The 'gave up later' mass G is unseen; we assume it looks like the weak part of the shown range (villain weak pair/draw/air)."""
    L = m['L']; ws = [w for *_, w in L]
    S = random.choices(L, weights=ws, k=min(nleaf, 4 * len(L)))
    acc = defaultdict(lambda: [0.0, 0]); accw = defaultdict(lambda: [0.0, 0])
    for i, vh, w in S:
        bd = R[i]['bd']
        if len(bd) < 10: continue
        dead = set(cards(vh) + cards(bd)); live = [c for c in DECK if c not in dead]
        nbs = bd[:4 + 2 * street]; nb = cards(nbs); fb = cards(bd); vr = evaluate_cards(*(cards(vh) + fb))
        weak = GROUP[fine(vh, nbs)] in ('W', 'D', 'A')
        for _ in range(k):
            h = random.sample(live, 2); g = GROUP[fine(''.join(h), ''.join(nb))]
            hr = evaluate_cards(*(h + fb)); r = 1.0 if hr < vr else 0.5 if hr == vr else 0.0
            acc[g][0] += r; acc[g][1] += 1
            if weak: accw[g][0] += r; accw[g][1] += 1
    out = {}
    for g, a in acc.items():
        if a[1] < 30: continue
        sd = a[0] / a[1]; wk = accw[g][0] / accw[g][1] if accw[g][1] >= 15 else sd
        out[g] = (1 - m['G']) * sd + m['G'] * wk
    return out
# ---- reads definition
def allk(sp, pat):
    rx = re.compile(pat); return [k for k in O if k.startswith(sp + '|ALL|') and rx.fullmatch(k.split('|')[2])]
def K(sp, *lines): return [f'{sp}|ALL|{l}' for l in lines]
READS = [
 # id, spot zh, kind(face/dec), keys, line text, child-call keys (for dec), response prefix
 ('ip_donk', '你開池・BB 跟注', 'face', K('SRP_IP', 'VbS', 'VbB', 'VbO'), '翻牌：BB 直接領先下注（donk）'),
 ('ip_xr_min', '你開池・BB 跟注', 'face', K('SRP_IP', 'Vx Hb Vrn'), '翻牌：他過牌，你下注，他「最小加注」'),
 ('ip_xr_big', '你開池・BB 跟注', 'face', K('SRP_IP', 'Vx Hb Vrg'), '翻牌：他過牌，你下注，他「大加注」'),
 ('ip_xc_lead', '你開池・BB 跟注', 'face', K('SRP_IP', 'Vx Hb Vc/VbS', 'Vx Hb Vc/VbB', 'Vx Hb Vc/VbO'), '翻牌過牌跟注 → 轉牌他突然領先下注'),
 ('ip_probe', '你開池・BB 跟注', 'face', K('SRP_IP', 'Vx Hx/VbS', 'Vx Hx/VbB', 'Vx Hx/VbO'), '翻牌你過牌不下 → 轉牌他下注'),
 ('ip_turn_xr', '你開池・BB 跟注', 'face', K('SRP_IP', 'Vx Hb Vc/Vx Hb Vrg', 'Vx Hb Vc/Vx Hb Vrn'), '翻牌跟注 → 轉牌你再下注，他過牌加注'),
 ('ip_riv_small', '你開池・BB 跟注', 'face', allk('SRP_IP', r'.*/.*/(Vx Hx )?VbS') , '河牌：他領先下「小注」（≤半池）'),
 ('ip_riv_big', '你開池・BB 跟注', 'face', allk('SRP_IP', r'.*/.*/(Vx Hx )?VbB'), '河牌：他領先下「大注」（半池～一池）'),
 ('ip_riv_over', '你開池・BB 跟注', 'face', allk('SRP_IP', r'.*/.*/(Vx Hx )?VbO'), '河牌：他「超池」下注'),
 ('ip_turn_dec', '你開池・BB 跟注', 'dec', K('SRP_IP', 'Vx Hb Vc/Vx'), '翻牌你下注他跟 → 轉牌他過牌'),
 ('ip_riv_dec', '你開池・BB 跟注', 'dec', K('SRP_IP', 'Vx Hb Vc/Vx Hb Vc/Vx'), '翻牌、轉牌他都跟注 → 河牌他過牌'),
 ('bb_cb_small', '你在 BB 防守', 'face', K('SRP_BB', 'Hx VbS'), '翻牌：你過牌，開池者「小」c-bet'),
 ('bb_cb_big', '你在 BB 防守', 'face', K('SRP_BB', 'Hx VbB', 'Hx VbO'), '翻牌：你過牌，開池者「大」c-bet'),
 ('bb_probe', '你在 BB 防守', 'dec', K('SRP_BB', 'Hx Vx'), '翻牌：兩人都過牌 → 轉牌你先行動'),
 ('bb_delay', '你在 BB 防守', 'face', K('SRP_BB', 'Hx Vx/Hx VbS', 'Hx Vx/Hx VbB', 'Hx Vx/Hx VbO'), '翻牌他不 c-bet → 轉牌才下注（延遲 c-bet）'),
 ('bb_barrel2', '你在 BB 防守', 'face', allk('SRP_BB', r'Hx Vb[SBO] Hc/Hx Vb[SBO]'), '翻牌 c-bet 你跟 → 轉牌他再下注'),
 ('bb_barrel3', '你在 BB 防守', 'face', allk('SRP_BB', r'Hx Vb[SBO] Hc/Hx Vb[SBO] Hc/Hx Vb[BO]'), '翻牌、轉牌都下注 → 河牌再下大注（三槍）'),
 ('bb_donk_raised', '你在 BB 防守', 'face', K('SRP_BB', 'Hb Vrg', 'Hb Vrn'), '翻牌你先下注，開池者加注'),
 ('3b_raised', '你 3-bet 了', 'face', K('3BP_3b_OOP', 'Hb Vrg', 'Hb Vrn') + K('3BP_3b_IP', 'Vx Hb Vrg', 'Vx Hb Vrn'), '翻牌你 c-bet，他加注'),
 ('3b_riv_dec', '你 3-bet 了', 'dec', K('3BP_3b_OOP', 'Hb Vc/Hb Vc') , '你 3-bet（不在位置）→ 翻牌、轉牌他都跟 → 河牌你先行動'),
 ('3c_cbet', '你跟注別人的 3-bet', 'face', K('3BP_call_IP', 'VbS', 'VbB') + K('3BP_call_OOP', 'Hx VbS', 'Hx VbB'), '翻牌：3-bet 的人 c-bet'),
 ('3c_over', '你跟注別人的 3-bet', 'face', K('3BP_call_IP', 'VbO') + K('3BP_call_OOP', 'Hx VbO'), '翻牌：3-bet 的人超池下注 / 推全下'),
 ('iso_donk', '你隔離溜入者', 'face', K('ISO_IP', 'VbS', 'VbB', 'VbO') + K('ISO_OOP', 'Hx VbS', 'Hx VbB', 'Hx VbO'), '翻牌：溜入者先下注'),
 ('iso_xc_lead', '你隔離溜入者', 'face', K('ISO_IP', 'Vx Hb Vc/VbS', 'Vx Hb Vc/VbB', 'Vx Hb Vc/VbO'), '溜入跟注 → 翻牌過牌跟注 → 轉牌突然下注'),
 ('iso_xr', '你隔離溜入者', 'face', K('ISO_IP', 'Vx Hb Vrg', 'Vx Hb Vrn'), '翻牌：溜入者過牌加注'),
 ('iso_turn_dec', '你隔離溜入者', 'dec', K('ISO_IP', 'Vx Hb Vc/Vx'), '翻牌你下注他跟 → 轉牌他過牌'),
]
# child keys for dec nodes: prefix + sep + 'Hb'; collect V response counts by rescanning
def child_prefix(key):
    sp, tx, l = key.split('|'); toks = l.split('/')[-1].split(' ')
    closes = toks[-1] == 'Vc' or (toks[-1] == 'Vx' and len(toks) >= 2 and toks[-2] == 'Hx')
    return f'{sp}|{tx}|{l}' + ('/' if closes else ' ') + 'Hb'
need = set(); 
for rd in READS:
    if rd[2] == 'dec':
        for k in rd[3]: need.add(child_prefix(k))
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('eng_tok', 'engine.py')
src = open('engine.py').read().split('SPOTS = defaultdict')[0].replace("R = pickle.load(open('data/hu.pkl', 'rb'))", '')
g = {'__file__': os.path.abspath('engine.py')}; exec(src, g)
RESP = defaultdict(Counter)
for r in R:
    if r['stk'] < 40: continue
    for sp, hw in g['views'](r):
        s = ''; last = 1
        toks = [(st, g['tok'](role, hw, a, x, ai)) for st, role, a, x, ai in r['ac']]
        for j, (st, t) in enumerate(toks):
            s = s + ('/' if st != last and s else (' ' if s else '')) + g['coarse'](t); last = st
            key = f'{sp}|ALL|{s}'
            if key in need and j + 1 < len(toks): RESP[key][toks[j + 1][1]] += 1
OUTR = []
for rid, spz, kind, keys, text in READS:
    m = merge(keys)
    if not m: print('MISSING', rid); continue
    st = m['street']; eq = hw_eq(m, st)
    rec = dict(id=rid, spot=spz, kind=kind, line=text, street=st, n=m['n'], nsd=m['nsd'], ess=m['ess'], grp=m['grp'],
               fine=m['fine'], combos=m['combos'], keys=[k.split('|', 1)[1] for k in m['keys']], eq={k: round(v, 3) for k, v in eq.items()})
    # board example: highest weight leaf
    i, vh, w = max(m['L'], key=lambda x: x[2] * random.random())
    rec['board'] = R[i]['bd'][:4 + 2 * st]
    if kind == 'face':
        toks = [k.split('|')[2].split(' ')[-1].split('/')[-1] for k in m['keys']]
        tk = Counter(toks).most_common(1)[0][0]; nd, xx = need_of(tk); rec['need'] = round(nd, 3)
        mg = {1: 0.10, 2: 0.06, 3: 0.0}[st]; rec['margin'] = mg
        rec['act'] = {gname: ('加注' if e >= 0.65 else '跟注' if e >= nd + mg + 0.03 else '棄牌' if e < nd + mg - 0.03 else '邊緣') for gname, e in eq.items()}
        rec['ev_call'] = {gname: round(e * (1 + 2 * xx) - xx, 3) if tk.startswith('Vb') else round(e * (1 + xx[0] + xx[1] * xx[0] + (xx[1] - 1) * xx[0]) - (xx[1] - 1) * xx[0], 3) for gname, e in eq.items()}
    else:
        resp = Counter(); call_keys = []
        for k in m['keys']:
            cp = child_prefix(k); resp.update(RESP.get(cp, {})); call_keys.append(cp + ' Vc' if True else '')
        tot = sum(resp.values()) or 1
        f = resp.get('Vf', 0) / tot; c = resp.get('Vc', 0) / tot; rr = 1 - f - c
        mc = merge(call_keys); b = 0.6
        rec['resp'] = {'fold': round(f, 3), 'call': round(c, 3), 'raise': round(rr, 3), 'n': tot}
        if mc:
            eqc = hw_eq(mc, st if not call_keys[0].endswith('/Hb Vc') else st + 1)
            rec['call_range'] = dict(grp=mc['grp'], n=mc['n'], nsd=mc['nsd'])
            act = {}; evs = {}
            for gname in eq:
                ec = eqc.get(gname)
                if ec is None: continue
                ev_bet = f + c * (ec * (1 + 2 * b) - b) - rr * b; ev_chk = eq[gname] if st == 3 else eq[gname]
                evs[gname] = (round(ev_bet, 3), round(ev_chk, 3), round(ec, 3))
                if ec >= 0.5: act[gname] = '下注（價值）'
                elif gname in ('A', 'D') and f > b / (1 + b) + 0.03: act[gname] = '下注（詐唬）'
                elif ev_bet > ev_chk + 0.02: act[gname] = '下注（保護）' if gname == 'W' else '過牌'
                else: act[gname] = '過牌'
            rec['act'] = act; rec['ev'] = evs
    OUTR.append(rec)
    print(rid, m['n'], m['nsd'], m['ess'], rec['grp'], rec.get('need'), {k: round(v, 2) for k, v in eq.items()}, rec.get('act'), rec.get('resp'), flush=True)
json.dump(OUTR, open('data/reads.json', 'w'), ensure_ascii=False, indent=1)
