import json, numpy as np
R = json.load(open('results.json')); S = json.load(open('summary.json')); N = R['names']; RK = '23456789TJQKA'
W = np.array([6 if len(n) == 2 else 4 if n[2] == 's' else 12 for n in N]) / 1326
REAS = ['base', 'shape', 'a50', 'shape_a50', 'adapt25', 'pen5', 'a50_pen5', 'shape_pen5', 'shape_adapt25_pen5']
SHOW = ['base', 'a25', 'a50', 'a75', 'a100', 'shape', 'adapt25', 'adapt50', 'pen5', 'pen10', 'a50_pen5', 'shape_adapt25_pen5', 'adapt50_pen10', 'bbsb50', 'bbsb45', 'gtostrat']
F = {}
for h in ['UTG', 'HJ', 'CO', 'BTN', 'SB']:
    D = {k: np.array(v['dev']) for k, v in R[h].items()}; pf = R[h]['base']['pf']
    votes = np.sum([D[k] > 0 for k in REAS], 0)
    rec = (votes >= 7).astype(float); core = (votes == 9).astype(float); exb = (D['base'] > 0).astype(float); gto = np.array(R['gto_open'][h])
    ev = lambda rng, k: float(100 * pf * (W * rng * D[k]).sum())
    tab = {k: dict(best_open=100 * float((W * (D[k] > 0)).sum()), best=ev(D[k] > 0, k), gto=ev(gto, k), exploit=ev(exb, k), rec=ev(rec, k), core=ev(core, k)) for k in SHOW if k in D}
    pct = lambda x: 100 * float((W * x).sum())
    F[h] = dict(pf=pf, gto=pct(gto), exploit=pct(exb), rec=pct(rec), core=pct(core), tab=tab,
                rec_cells=[N[i] for i in range(169) if rec[i]], core_cells=[N[i] for i in range(169) if core[i]],
                rec_minus_gto=[N[i] for i in range(169) if rec[i] and gto[i] < .5], gto_minus_rec=[N[i] for i in range(169) if not rec[i] and gto[i] >= .5],
                exploit_minus_rec=[N[i] for i in range(169) if exb[i] and not rec[i]], votes=[int(v) for v in votes],
                dev_base=[round(float(x), 3) for x in D['base']], dev_pess=[round(float(x), 3) for x in D['shape_adapt25_pen5']], gto_open=[float(x) for x in gto])
    print(f"\n{h}: GTO {F[h]['gto']:.1f}  exploit {F[h]['exploit']:.1f}  rec {F[h]['rec']:.1f}  core {F[h]['core']:.1f}  P(fold to)={pf:.2f}")
    for k, v in tab.items(): print(f"  {k:20s} bestopen {v['best_open']:5.1f}  best {v['best']:+6.2f} gto {v['gto']:+6.2f} expl {v['exploit']:+6.2f} rec {v['rec']:+6.2f} core {v['core']:+6.2f}")
    print('  rec - GTO:', ' '.join(F[h]['rec_minus_gto'])); print('  GTO - rec:', ' '.join(F[h]['gto_minus_rec'])); print('  exploit - rec:', ' '.join(F[h]['exploit_minus_rec']))
    print('  rec - core:', ' '.join(sorted(set(F[h]['rec_cells']) - set(F[h]['core_cells']))))
json.dump(F, open('final.json', 'w'))
