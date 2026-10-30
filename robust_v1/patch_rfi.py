"""Stage 2: hero RFI nodes (exp) = audited robust sets, pure 100/0. EV column = 'reasonable pessimistic' scenario
(shape_adapt25_pen5: defenders' hand ranking like GTO, they adapt 0.25pt fold per pt of extra width, hero -5% OOP realization).
fold EV kept from the base model; open EV = fold EV + scenario delta. Labels: robust exploit."""
import json, numpy as np
PF = json.load(open('pf_data_stage1.json')); old = json.load(open('/workspace/outputs/poker_v8/build/pf_data.json'))
F = json.load(open('/workspace/outputs/poker_solver/rfi_audit/final.json')); N = PF['names']
USE = {'UTG': 'rec_cells', 'HJ': 'rec_cells', 'CO': 'rec_cells', 'BTN': 'core_cells', 'SB': 'core_cells'}
NC = np.array([6 if len(n) == 2 else 4 if n[2] == 's' else 12 for n in N], float)
# gto untouched
for k in PF['nodes']: assert PF['nodes'][k]['gto'] == old['nodes'][k]['gto'], k
for seat, key in USE.items():
    nd = PF['nodes'][seat + 'rfi']; A = nd['acts']; fi, oi = A.index('fold'), A.index('open'); cells = set(F[seat][key])
    dp = F[seat]['dev_pess']; dp = dp if isinstance(dp, list) else [dp[n] for n in N]
    e = nd['exp']; s = []; ev = []
    for i, n in enumerate(N):
        row = [0, 0]; row[oi if n in cells else fi] = 100; s.append(row)
        d = int(round(dp[i] * 100))
        if (d > 0) != (n in cells) and abs(d) <= 1: d = 0          # 4 cells within 0.01bb: show as tie
        assert (d >= 0) if n in cells else (d <= 0), (seat, n, dp[i])
        f = e['ev'][i][fi]; r = [None, None]; r[fi] = f; r[oi] = f + d; ev.append(r)
    e['s'] = s; e['ev'] = ev; e['fl'] = {}
    w = NC * np.array(e['r']) / 100
    e['freq'] = {a: round(float((w * np.array([x[j] for x in s]) / 100).sum() / w.sum() * 100), 1) for j, a in enumerate(A)}
    e['robust'] = dict(set='rec' if key == 'rec_cells' else 'core', ev_scn='shape_adapt25_pen5')
    print(seat, e['freq'], 'was', old['nodes'][seat + 'rfi']['exp']['freq'])
# keep nodes NOT downstream of the hero's own open byte-identical (defence nodes: re-solve noise only)
for k, nd in PF['nodes'].items():
    if not (k.endswith('rfi') or k.startswith(nd['seat'] + 'open>')): nd['exp'] = old['nodes'][k]['exp']
PF['ver'] = 'v8-1031r'
PF['build']['robust'] = dict(date='2026-10-31', sets=USE, ev_scn='shape_adapt25_pen5', src='rfi_audit/final.json (9 scenarios)')
# report changed exp nodes
ch = []
for k in PF['nodes']:
    a, b = PF['nodes'][k]['exp'], old['nodes'][k]['exp']
    if a['s'] != b['s'] or a['r'] != b['r']:
        ns = sum(1 for x, y in zip(a['s'], b['s']) if x != y); ch.append((k, ns, b['freq'], a['freq']))
for c in ch: print('CHANGED', c)
js = 'window.PF=' + json.dumps(PF, separators=(',', ':'), ensure_ascii=False) + ';'
open('pf_data.js', 'w').write(js); json.dump(PF, open('pf_data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('heroes', PF['heroes'], 'size', len(js) // 1000, 'KB')
