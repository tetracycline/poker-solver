"""Validation numbers for REPORT_postflop.md: exploitability, c-bet / check-raise by texture vs published, no-rake comparison,
hand-strength monotonicity, exploit locks (n, Wilson CI) and EV gains."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, os, glob, sys, math, statistics as stt
sys.path.insert(0, os.path.dirname(__file__))
from ranges import SPOTS
from pipeline import flops_for
from locks import wilson
OUT = f'{PFDIR}/out'; REP = f'{PFDIR}/report'
R = '23456789TJQKA'
def load(f):
    try: return json.load(open(f))
    except Exception: return None
def tex(fl):
    rs = sorted([R.index(fl[i]) for i in (0, 2, 4)], reverse=True); ss = len({fl[i + 1] for i in (0, 2, 4)})
    hi = 'A 高' if rs[0] == 12 else 'K/Q 高' if rs[0] >= 10 else 'J/T 高' if rs[0] >= 8 else '9 以下'
    pair = len(set(rs)) < 3
    suit = {1: '單色', 2: '兩色', 3: '彩虹'}[ss]
    conn = (rs[0] - rs[2] <= 4 and not pair)
    return dict(hi=hi, pair='有對' if pair else '無對', suit=suit, conn='連張' if conn else '不連')
def node(fr, line):
    for n in fr['nodes']:
        if n['line'] == line and n['board'] and len(n['board']) == 6: return n
def freqs(fr, line):
    n = node(fr, line)
    if not n: return None
    p = n['player']; nh = len(fr['hands'][p]); w = n['w'][p]; tw = sum(w) or 1
    return {a: 100 * sum(w[h] * n['strat'][i * nh + h] for h in range(nh)) / tw for i, a in enumerate(n['acts'])}
def flop_stats(spot, ver):
    pfr = SPOTS[spot]['pfr']; rows = []
    for fl in flops_for(spot):
        fr = load(f'{OUT}/{spot}/{ver}/{fl}.json')
        if not fr: continue
        root = 'x' if pfr == 'ip' else ''
        f = freqs(fr, root)
        if not f: continue
        cb = sum(v for a, v in f.items() if a[0] == 'b'); r = dict(flop=fl, cbet=cb, b33=f.get('b33', 0), b75=f.get('b75', 0), expl=fr['info'].get('gto_expl_pct'), gap=fr['info'].get('hero_gap_pct'))
        for sz in ('b33', 'b75'):
            g = freqs(fr, (root + ' ' + sz).strip())
            if g: r['xr_' + sz] = g.get('r', 0) + g.get('a', 0); r['fold_' + sz] = g.get('f', 0)
        r.update(tex(fl)); rows.append(r)
    return rows
def agg(rows, key, by=None):
    if not rows: return {}
    if by is None: return {'全部': (stt.mean(r[key] for r in rows if key in r), len(rows))}
    out = {}
    for r in rows:
        if key in r: out.setdefault(r[by], []).append(r[key])
    return {k: (stt.mean(v), len(v)) for k, v in out.items()}
def spearman(x, y):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
            for k in range(i, j + 1): r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    a, b = rk(x), rk(y); n = len(x)
    if n < 3: return None
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((p - ma) * (q - mb) for p, q in zip(a, b)); va = math.sqrt(sum((p - ma) ** 2 for p in a)); vb = math.sqrt(sum((q - mb) ** 2 for q in b))
    return cov / (va * vb) if va and vb else None
def monotonic(spot, ver='gto'):
    """facing-a-bet nodes: continue% (call+raise) vs equity. Report Spearman rho (reach-weighted sample) and equity-decile table."""
    res = {'flop': [], 'turn': [], 'river': []}; dec = {k: [[0, 0] for _ in range(10)] for k in res}; viol = {k: [0, 0] for k in res}
    files = [f for f in glob.glob(f'{OUT}/{spot}/{ver}/*.json') if not f.endswith('.job.json')]
    for f in files:
        fr = load(f)
        for n in fr['nodes']:
            if 'f' not in n['acts'] or n['line'].count('/') == 0 and '_' in os.path.basename(f): continue
            st = ['flop', 'turn', 'river'][len(n['board']) // 2 - 3]
            p = n['player']; nh = len(fr['hands'][p]); w = n['w'][p]; mx = max(w) if w else 0
            if mx <= 0: continue
            fi = n['acts'].index('f'); xs, ys = [], []
            for h in range(nh):
                if w[h] < 0.05 * mx: continue
                c = 1 - n['strat'][fi * nh + h]; e = n['eq'][h]; xs.append(e); ys.append(c)
                d = min(9, int(e * 10)); dec[st][d][0] += w[h] * c; dec[st][d][1] += w[h]
            rho = spearman(xs, ys)
            if rho is not None: res[st].append(rho)
            # violations: hand with >=20pp more equity than another but continuing >=50pp less (only on the river, where equity is final)
            if st == 'river':
                pr = sorted(zip(xs, ys)); best_low = -1
                for e, c in pr:
                    viol[st][1] += 1
            # (river check below)
            if st == 'river':
                arr = sorted(zip(xs, ys)); import bisect
                es = [a for a, _ in arr]; prefmax = []
                m = -1
                for _, c in arr: m = max(m, c); prefmax.append(m)
                for e, c in arr:
                    k = bisect.bisect_right(es, e - 0.20) - 1
                    if k >= 0 and prefmax[k] - c >= 0.5: viol[st][0] += 1
    out = {}
    for st in res:
        v = res[st]
        out[st] = dict(nodes=len(v), rho_median=stt.median(v) if v else None, rho_p10=sorted(v)[len(v) // 10] if v else None,
                       deciles=[round(100 * a / b, 1) if b else None for a, b in dec[st]])
    out['river']['violations'] = viol['river']
    return out
def exploit_rows(spot):
    rows = []
    for ver, hero in (('exp_ip', 1), ('exp_oop', 0)):
        for fl in flops_for(spot):
            fr = load(f'{OUT}/{spot}/{ver}/{fl}.json')
            if not fr: continue
            i = fr['info']
            if i.get('ev_exploit') is None: continue
            rows.append(dict(ver=ver, flop=fl, gain=(i['ev_exploit'][hero] - i['ev_gto_vs_pool'][hero]) / 100, gap=i['hero_gap_pct'], locks=i.get('locks')))
    return rows
def main():
    S = {}
    for spot in SPOTS:
        g = flop_stats(spot, 'gto')
        if not g: continue
        S[spot] = dict(n=len(g), cbet=agg(g, 'cbet'), b33=agg(g, 'b33'), b75=agg(g, 'b75'),
                       cbet_hi=agg(g, 'cbet', 'hi'), cbet_pair=agg(g, 'cbet', 'pair'), cbet_suit=agg(g, 'cbet', 'suit'), cbet_conn=agg(g, 'cbet', 'conn'),
                       xr33=agg(g, 'xr_b33'), xr75=agg(g, 'xr_b75'), fold33=agg(g, 'fold_b33'), fold75=agg(g, 'fold_b75'),
                       xr33_pair=agg(g, 'xr_b33', 'pair'), xr33_suit=agg(g, 'xr_b33', 'suit'),
                       expl=[r['expl'] for r in g], rows=g)
        nr = flop_stats(spot, 'norake')
        if nr: S[spot]['norake'] = dict(n=len(nr), cbet=agg(nr, 'cbet'), b33=agg(nr, 'b33'), b75=agg(nr, 'b75'), xr33=agg(nr, 'xr_b33'), fold33=agg(nr, 'fold_b33'), xr75=agg(nr, 'xr_b75'), rows=nr)
        ex = exploit_rows(spot)
        S[spot]['exploit'] = dict(n=len(ex), gain_ip=[r['gain'] for r in ex if r['ver'] == 'exp_ip'], gain_oop=[r['gain'] for r in ex if r['ver'] == 'exp_oop'],
                                  gap=[r['gap'] for r in ex], locks={r['ver']: r['locks'] for r in ex})
        # subgame exploitability
        sub = [load(f)['info'] for f in glob.glob(f'{OUT}/{spot}/gto/*_*.json') if not f.endswith('.job.json')]
        S[spot]['sub_expl'] = [i.get('gto_expl_pct') for i in sub if i]
        S[spot]['sub_gap'] = [load(f)['info'].get('hero_gap_pct') for f in glob.glob(f'{OUT}/{spot}/exp_*/*_*.json') if not f.endswith('.job.json')]
        print(spot, 'flops', len(g), 'cbet', S[spot]['cbet'], 'xr33', S[spot]['xr33'])
    for sp in S:
        S[sp]['mono'] = monotonic(sp); print(sp, 'mono', S[sp]['mono'], flush=True)
        S[sp]['mono_exp'] = {v: monotonic(sp, v) for v in ('exp_ip', 'exp_oop')}
    json.dump(S, open(f'{REP}/validation.json', 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__': main()
