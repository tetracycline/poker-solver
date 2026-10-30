import json, numpy as np
R = json.load(open('results.json')); N = R['names']; RK = '23456789TJQKA'
W = np.array([6 if len(n) == 2 else 4 if n[2] == 's' else 12 for n in N]) / 1326
REAS = ['base', 'shape', 'a50', 'shape_a50', 'adapt25', 'pen5', 'a50_pen5', 'shape_pen5', 'shape_adapt25_pen5']
ALL = ['base','a25','a50','a75','a100','adapt25','adapt50','pen5','pen10','a50_pen5','adapt25_pen5','adapt50_pen10','shape','shape_a50','shape_pen5','shape_adapt25_pen5','gtostrat','bbsb50','bbsb45']
out = {}
for h in ['UTG', 'HJ', 'CO', 'BTN', 'SB']:
    D = {k: np.array(v['dev']) for k, v in R[h].items()}; pf = R[h]['base']['pf']
    gto = np.array(R['gto_open'][h]); exb = (D['base'] > 0).astype(float)
    M = np.mean([D[k] for k in REAS], 0); rob = (M > 0).astype(float)
    inter = np.all([D[k] > 0 for k in REAS], 0).astype(float)
    def ev(rng, k): return float(100 * pf * (W * rng * D[k]).sum())   # bb per 100 hands dealt at this seat (vs folding all)
    rows = {}
    for k in ALL:
        if k in D: rows[k] = dict(open=100 * float((W * (D[k] > 0)).sum()), ev_best=ev((D[k] > 0), k), ev_gto=ev(gto, k), ev_exploit=ev(exb, k), ev_rob=ev(rob, k), ev_inter=ev(inter, k))
    out[h] = dict(pf=pf, gto=100 * float((W * gto).sum()), exploit=100 * float((W * exb).sum()), rob=100 * float((W * rob).sum()), inter=100 * float((W * inter).sum()), rows=rows,
                  rob_set=[N[i] for i in range(169) if rob[i]], add_vs_gto=[N[i] for i in range(169) if rob[i] and gto[i] < .5], drop_vs_gto=[N[i] for i in range(169) if not rob[i] and gto[i] >= .5],
                  exploit_only=[N[i] for i in range(169) if exb[i] and not rob[i]],
                  marginal=sorted([(N[i], round(float(D['base'][i]), 3), round(float(M[i]), 3)) for i in range(169) if abs(M[i]) < 0.06 or (exb[i] and not rob[i])], key=lambda x: -x[2]),
                  mean_dev=[float(x) for x in M])
    print(f"\n== {h}  P(folded to)={pf:.3f}  GTO {out[h]['gto']:.1f}%  exploit {out[h]['exploit']:.1f}%  robust(mean) {out[h]['rob']:.1f}%  intersection {out[h]['inter']:.1f}%")
    for k, v in rows.items(): print(f"  {k:20s} open {v['open']:5.1f}%  EV best {v['ev_best']:+6.2f}  gto {v['ev_gto']:+6.2f}  exploit {v['ev_exploit']:+6.2f}  robust {v['ev_rob']:+6.2f}  inter {v['ev_inter']:+6.2f}")
    print('  add vs GTO:', ' '.join(out[h]['add_vs_gto'])); print('  drop vs GTO:', ' '.join(out[h]['drop_vs_gto'])); print('  exploit-only (cut):', ' '.join(out[h]['exploit_only']))
    print('  marginal (hand, base dEV, mean dEV):', out[h]['marginal'][:60])
json.dump(out, open('summary.json', 'w'), ensure_ascii=False)
