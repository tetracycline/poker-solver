"""Cross-sizing consistency (no contradictory strategies): at every decision facing a bet, the same combo (same range, same board,
same line except the size of the last bet) should not continue much MORE often against the BIGGER bet than against the smaller one.
Range level: fold% vs big >= fold% vs small.  Combo level: flag combos continuing >=50pp more vs the bigger size (reach-weighted)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, glob, os, re, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
from ranges import SPOTS
OUT = f'{PFDIR}/out'; REP = f'{PFDIR}/report'
def sz(t):
    m = re.fullmatch(r'b(\d+)', t); return int(m.group(1)) if m else None
def main():
    R = {}
    for spot in SPOTS:
        for ver in ('gto', 'exp_ip', 'exp_oop'):
            files = [f for f in glob.glob(f'{OUT}/{spot}/{ver}/*.json') if not f.endswith('.job.json')]
            if not files: continue
            pairs = 0; rng_bad = 0; cmb = 0; cmb_bad = 0; wtot = 0.0; wbad = 0.0; ex = []
            for f in files:
                fr = json.load(open(f)); H = fr['hands']; G = collections.defaultdict(dict)
                BY = {(n['line'], n['board']): n for n in fr['nodes']}
                for n in fr['nodes']:
                    if 'f' not in n['acts']: continue
                    m = re.fullmatch(r'(.*?)b(\d+)', n['line'])  # line ends with a sized bet (after ' ' or '/')
                    if not m: continue
                    G[(m.group(1), n['board'], n['player'])][int(m.group(2))] = n
                hero = {'exp_ip': 1, 'exp_oop': 0}.get(ver)
                for (pre, bd, p), D in G.items():
                    par = BY.get((pre.rstrip(' '), bd)); pw = sum(par['w'][p]) if par else 0
                    # only sizes the bettor actually uses (>= 3% of the time); unreached nodes carry arbitrary strategies
                    D = {k: v for k, v in D.items() if pw > 0 and sum(v['w'][p]) >= 0.03 * pw}
                    if hero is not None and p != hero: continue  # exploit files: only the hero's decisions are drilled (villain = locked pool model)
                    ks = sorted(D)
                    for a, b in zip(ks, ks[1:]):
                        na, nb = D[a], D[b]; nh = len(H[p]); wa = na['w'][p]; wb = nb['w'][p]
                        fa = na['acts'].index('f'); fb = nb['acts'].index('f'); mx = max(wa) if wa else 0
                        if mx <= 0: continue
                        Fa = sum(wa[h] * na['strat'][fa * nh + h] for h in range(nh)) / sum(wa)
                        Fb = sum(wb[h] * nb['strat'][fb * nh + h] for h in range(nh)) / (sum(wb) or 1)
                        pairs += 1
                        if Fb + 0.01 < Fa: rng_bad += 1; ex.append(dict(f=os.path.basename(f), line=pre, board=bd, small=a, big=b, fold_small=round(100 * Fa, 1), fold_big=round(100 * Fb, 1)))
                        for h in range(nh):
                            if wa[h] < 0.05 * mx: continue
                            ca = 1 - na['strat'][fa * nh + h]; cb = 1 - nb['strat'][fb * nh + h]
                            cmb += 1; wtot += wa[h]
                            if cb - ca >= 0.5: cmb_bad += 1; wbad += wa[h]
            R[f'{spot}|{ver}'] = dict(pairs=pairs, range_bad=rng_bad, combos=cmb, combo_bad=cmb_bad, combo_bad_w_pct=round(100 * wbad / max(wtot, 1e-9), 3), examples=ex[:8])
            print(spot, ver, pairs, rng_bad, cmb_bad, cmb, R[f'{spot}|{ver}']['combo_bad_w_pct'], flush=True)
    json.dump(R, open(f'{REP}/consistency.json', 'w'), ensure_ascii=False, indent=1)
if __name__ == '__main__': main()
