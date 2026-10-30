"""Post-process solver outputs into compact per-flop JSON for the postflop drill page."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, os, re, glob, sys, math
sys.path.insert(0, os.path.dirname(__file__))
from classify import category, CATS
from ranges import SPOTS
from pipeline import flops_for
OUT = f'{PFDIR}/out'; SITE = f'{PFDIR}/site'
DATA = f'{SITE}/postflop/data'
MINW = 0.05  # drop combos reaching the node with < 5% of the most-reaching combo's weight
def pfr_side(spot): return 1 if SPOTS[spot]['pfr'] == 'ip' else 0
def load(f):
    try: return json.load(open(f))
    except Exception: return None
UNREL_BB = 0.25; UNREL_POT = 0.05; MIN_PR_Q = 0.002
def lock_note(locks, line):
    for L in locks or []:
        if re.search(L['pat'], line): return L
    return None
def pack_node(n, H, cat, locks, ver):
    p = n['player']; hs = H[p]; nh = len(hs); w = n['w'][p]; mx = max(w) if w else 0
    if mx <= 0: return None
    keep = [i for i in range(nh) if w[i] >= MINW * mx]
    na = len(n['acts'])
    s, ev, eq, ww = [], [], [], []
    for i in keep:
        row = [n['strat'][a * nh + i] for a in range(na)]; t = sum(row) or 1
        pc = [round(100 * x / t) for x in row]
        d = 100 - sum(pc); pc[max(range(na), key=lambda a: row[a])] += d
        s += pc; ev += [round(n['ev'][a * nh + i]) for a in range(na)]
        eq.append(round(100 * n['eq'][i])); ww.append(round(100 * w[i] / mx))
    out = dict(l=n['line'], b=n['board'], p=p, c=cat, a=n['acts'], pot=n['pot'], bt=n['bets'],
               h=''.join(hs[i] for i in keep), s=s, ev=ev, eq=eq, w=ww)
    # unreliable combos: solver's main (most frequent) action loses clearly vs its best-EV action
    # (incomplete convergence at low-reach nodes) -> shown in charts with a mark, never asked
    thr = max(UNREL_BB * 100, UNREL_POT * (n['pot'] + sum(n['bets'])))
    u = []
    for j in range(len(keep)):
        r = s[j * na:(j + 1) * na]; e = ev[j * na:(j + 1) * na]; m = r.index(max(r))
        if max(e) - e[m] > thr: u.append(j)
    if u: out['u'] = u
    if ver == 'exp':
        nx = {}
        for a in n['acts']:
            if a in ('f',): continue
            L = lock_note(locks, (n['line'] + ' ' + a) if n['line'] and not n['line'].endswith('/') else n['line'] + a)
            if L: nx[a] = {k: L[k] for k in ('src', 'n', 'fold', 'raise_', 'bet', 'lo', 'hi') if k in L and L[k] is not None}
        if nx: out['nx'] = nx
    # range-level frequency (for summary tables)
    tw = sum(w) or 1
    out['f'] = [round(100 * sum(w[i] * n['strat'][a * nh + i] for i in range(nh)) / tw, 1) for a in range(na)]
    return out
def wsum(n): return sum(n['w'][0]) or 1e-12
def root_of(fr, line):
    for n in fr['nodes']:
        if n['line'] == line: return n
def nodes_from(fr, spot, ver, sub, wanted_player=None, flopfr=None):
    if fr is None: return []
    H = fr['hands']; locks = fr['info'].get('locks') or []; res = []
    if sub:
        l0 = fr['line0'] + '/'; tr = None
        for n in flopfr['nodes']:
            if n['line'] == l0 and n['board'][-2:] == fr['turn']: tr = n
        base = wsum(tr) / wsum(root_of(flopfr, '')) / max(1, len(flopfr.get('turns') or [1]))
        rs = wsum(root_of(fr, l0))
    else:
        base = 1.0; rs = wsum(root_of(fr, ''))
    rv0 = fr.get('rivers', [None])[0] if sub else None
    for n in fr['nodes']:
        st = n['line'].count('/')
        if not sub and st != 0: continue
        if sub and st == 0: continue
        if sub and len(n['board']) == 10 and n['board'][-2:] != rv0: continue
        if wanted_player is not None and n['player'] != wanted_player: continue
        if len(n['acts']) < 2: continue
        cat = category(n['line'], n['player'], pfr_side(spot))
        if not cat: continue
        if cat == 'vs_raise' and st == 2: continue
        pk = pack_node(n, H, cat, locks, ver)
        if pk:
            pk['pr'] = float('%.4g' % (base * wsum(n) / rs))
            if pk['pr'] >= 1e-4 or not sub: res.append(pk)
    return res
def lock_summary(fr):
    if not fr: return []
    return [{k: L.get(k) for k in ('pat', 'src', 'n', 'fold', 'raise_', 'bet')} for L in fr['info'].get('locks') or []]
def mark_size_conflicts(nodes):
    """Never ask a combo whose answer contradicts a sibling sizing: same line/board/player, facing the bigger bet it continues
    >=50pp MORE than facing the smaller bet (both sizes actually used). Marked in both nodes via 'uc' (shown, never asked)."""
    G = {}
    for n in nodes:
        m = re.fullmatch(r'(.*?)b(\d+)', n['l'])
        if m and 'f' in n['a']: G.setdefault((m.group(1), n['b'], n['p']), {})[int(m.group(2))] = n
    k = 0
    for D in G.values():
        ks = sorted(D)
        for a, b in zip(ks, ks[1:]):
            A, B = D[a], D[b]
            if min(A['pr'], B['pr']) < 1e-4: continue
            ha = [A['h'][i:i + 4] for i in range(0, len(A['h']), 4)]; hb = {B['h'][i:i + 4]: j for j, i in enumerate(range(0, len(B['h']), 4))}
            na, nb = len(A['a']), len(B['a']); fa, fb = A['a'].index('f'), B['a'].index('f')
            for i, h in enumerate(ha):
                j = hb.get(h)
                if j is None: continue
                if (100 - B['s'][j * nb + fb]) - (100 - A['s'][i * na + fa]) >= 50:
                    A.setdefault('uc', []); B.setdefault('uc', [])
                    if i not in A['uc']: A['uc'].append(i)
                    if j not in B['uc']: B['uc'].append(j)
                    k += 1
    return k
CONFLICTS = {'gto': 0, 'exp': 0}
def build_flop(spot, flop):
    d = f'{OUT}/{spot}'; R = {'spot': spot, 'flop': flop, 'v': {}, 'info': {}}
    def subs(ver): return sorted(f for f in glob.glob(f'{d}/{ver}/{flop}_*.json') if not f.endswith('.job.json'))
    g = load(f'{d}/gto/{flop}.json')
    if g is None: return None
    nodes = nodes_from(g, spot, 'gto', False)
    for f in subs('gto'): nodes += nodes_from(load(f), spot, 'gto', True, None, g)
    CONFLICTS['gto'] += mark_size_conflicts(nodes)
    R['v']['gto'] = nodes
    R['info']['gto'] = {k: g['info'].get(k) for k in ('gto_expl_pct', 'gto_iters', 'ev_eq')}
    e = []; ok = True
    for ver, pl in (('exp_oop', 0), ('exp_ip', 1)):
        fr = load(f'{d}/{ver}/{flop}.json')
        if fr is None: ok = False; continue
        e += nodes_from(fr, spot, 'exp', False, pl)
        for f in subs(ver): e += nodes_from(load(f), spot, 'exp', True, pl, fr)
        R['info'][ver] = {k: fr['info'].get(k) for k in ('gto_expl_pct', 'hero_gap_pct', 'ev_eq', 'ev_gto_vs_pool', 'ev_exploit', 'lock_stats')}
        R['info'][ver]['locks'] = lock_summary(fr)
    if ok: CONFLICTS['exp'] += mark_size_conflicts(e); R['v']['exp'] = e
    R['turns'] = g.get('turns')
    return R
def main():
    os.makedirs(DATA, exist_ok=True)
    idx = {'spots': {}, 'cats': [[k, zh, st] for k, zh, st in CATS]}
    tot = 0
    for spot in SPOTS:
        fl = flops_for(spot); have = []
        cnt = {}
        for flop in fl:
            R = build_flop(spot, flop)
            if R is None or 'exp' not in R['v']: continue
            os.makedirs(f'{DATA}/{spot}', exist_ok=True)
            fn = f'{DATA}/{spot}/{flop}.json'; json.dump(R, open(fn, 'w'), separators=(',', ':')); tot += os.path.getsize(fn)
            c = {}
            for v in ('gto', 'exp'):
                for n in R['v'][v]:
                    key = v + '|' + n['c']; c[key] = c.get(key, 0) + 1
                    cnt[key] = cnt.get(key, 0) + len(n['w'])
            have.append([flop, c])
        if have:
            s = SPOTS[spot]
            idx['spots'][spot] = {'flops': have, 'pfr': pfr_side(spot), 'kind': s['kind'], 'pot': s['pot'], 'stack': s['stack'], 'qcount': cnt,
                                  'oop': s['oop'], 'ip': s['ip']}
    json.dump(idx, open(f'{DATA}/index.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump(CONFLICTS, open(f'{PFDIR}/report/size_conflicts.json', 'w'))
    print('size conflicts marked (never asked)', CONFLICTS)
    print('bytes', tot, 'spots', {k: len(v['flops']) for k, v in idx['spots'].items()})
if __name__ == '__main__': main()
