"""Data checks on the site JSON: strategies sum to 100, no board-blocked combos, EV of the graded (main) action vs best EV,
and a Python re-implementation of THE grading rule used by app.js (written to grading_ref.json for the UI consistency test)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, glob, random, os, sys, gzip
D = os.environ.get('PF_DATA', f'{PFDIR}/site/postflop/data')
random.seed(7)
def ok_acts(n, i):
    k = len(n['a']); s = n['s'][i * k:(i + 1) * k]; m = max(range(k), key=lambda j: (s[j], -j))
    # JS picks the first max; emulate
    m = 0
    for j in range(k):
        if s[j] > s[m]: m = j
    return n['a'][m], [a for j, a in enumerate(n['a']) if j == m or s[j] >= 25], s
askable_gap = []; unrel = 0; ask = 0
bad_sum = 0; blocked = 0; tot = 0; evgap = []; big_gap = 0; nodes = 0; refs = []
files = sorted(glob.glob(f'{D}/*/*.json') + glob.glob(f'{D}/*/*.json.gz'))
for f in files:
    F = json.loads(gzip.open(f).read()) if f.endswith('.gz') else json.load(open(f)); sp = F['spot']
    for v, L in F['v'].items():
        for n in L:
            nodes += 1; k = len(n['a']); nh = len(n['h']) // 4; bd = {n['b'][i:i + 2] for i in range(0, len(n['b']), 2)}
            assert len(n['s']) == k * nh == len(n['ev']) and len(n['w']) == nh == len(n['eq'])
            for i in range(nh):
                tot += 1; s = n['s'][i * k:(i + 1) * k]
                if sum(s) != 100: bad_sum += 1
                h = n['h'][4 * i:4 * i + 4]
                if h[:2] in bd or h[2:] in bd: blocked += 1
                main, ok, _ = ok_acts(n, i); ev = n['ev'][i * k:(i + 1) * k]
                g = (max(ev) - ev[n['a'].index(main)]) / 100; evgap.append(g)
                if g > 0.25 and n['w'][i] >= 10: big_gap += 1
                isu = i in set(n.get('u', [])) | set(n.get('uc', []))
                unrel += isu
                if n['w'][i] >= 10 and not isu and n['pr'] >= 0.002: ask += 1; askable_gap.append(g)
            for _ in range(2):
                i = random.randrange(nh)
                if n['w'][i] >= 10 and i not in set(n.get('u', [])) | set(n.get('uc', [])) and n['pr'] >= 0.002:
                    main, ok, s = ok_acts(n, i); refs.append(dict(sp=sp, fl=F['flop'], v=v, l=n['l'], b=n['b'], h=n['h'][4 * i:4 * i + 4], main=main, ok=ok, acts=n['a'], s=s))
evgap.sort()
print(f'files {len(files)} nodes {nodes} combos {tot}')
print(f'strategy rows not summing to 100: {bad_sum}; board-blocked combos: {blocked}')
print(f'EV(best) - EV(graded main action): median {evgap[len(evgap)//2]:.3f}bb, p99 {evgap[int(.99*len(evgap))]:.3f}bb, max {evgap[-1]:.2f}bb; combos (w>=10) with gap >0.25bb: {big_gap}')
askable_gap.sort(); A = askable_gap
print(f'flagged unreliable (*未收斂, never asked): {unrel} of {tot} ({100*unrel/tot:.2f}%)')
if A: print(f'askable combos {ask}: EV gap median {A[len(A)//2]:.3f}bb p99 {A[int(.99*len(A))]:.3f}bb max {A[-1]:.2f}bb')
random.shuffle(refs); json.dump(refs[:400], open(f'{PFDIR}/check/grading_ref.json', 'w'))
print('ref sample', min(400, len(refs)))
sys.exit(1 if bad_sum or blocked else 0)
