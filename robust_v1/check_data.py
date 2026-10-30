"""Independent display-level check of site/pf_data.js (what the site renders)."""
import json, re, sys
src = open('/workspace/outputs/poker_solver/robust_v1/pf_data.js').read()
PF = json.loads(src[src.index('=') + 1:].rstrip().rstrip(';'))
N = PF['names']; IX = {n: i for i, n in enumerate(N)}; R = 'AKQJT98765432'
cnt = lambda n: 6 if len(n) == 2 else (4 if n[2] == 's' else 12)
pairs = [r + r for r in reversed(R)]                       # 22..AA weak->strong
kick, high = [], []
for t in 'so':
    for a in range(13):                                    # fixed high card, kicker up
        ch = [R[a] + R[b] + t for b in range(12, a, -1)]
        if len(ch) > 1: kick.append(ch)
    for b in range(1, 13):                                 # fixed low card, high card up
        ch = [R[a] + R[b] + t for a in range(b - 1, -1, -1)][::-1]
        ch = [R[a] + R[b] + t for a in range(b - 1, -1, -1)]
        ch = ch[::-1] if False else ch
        ch = [R[a] + R[b] + t for a in reversed(range(0, b))]  # e.g. low=9: T9,J9,..,A9
        if len(ch) > 1: high.append(ch)
bad = []; stats = dict(nodes=0, cells=0)
for name, nd in PF['nodes'].items():
    A = nd['acts']; fi = A.index('fold')
    for v in ('gto', 'exp'):
        d = nd[v]; stats['nodes'] += 1
        for i, s in enumerate(d['s']):
            stats['cells'] += 1
            if sum(s) != 100 or min(s) < 0: bad.append((v, name, N[i], 'sum', s))
        # freq recomputed from displayed strat
        w = [cnt(N[i]) * d['r'][i] / 100 for i in range(169)]
        tot = sum(w)
        for j, a in enumerate(A):
            f = sum(w[i] * d['s'][i][j] for i in range(169)) / tot
            if abs(f - d['freq'][a]) > 0.25: bad.append((v, name, a, 'freq', f, d['freq'][a]))
        cont = lambda h: 100 - d['s'][IX[h]][fi]
        live = lambda h: d['r'][IX[h]] >= 5
        for ch in kick + [pairs]:
            ch = [h for h in ch if live(h)]
            for x in range(len(ch)):
                for y in range(x + 1, len(ch)):            # ch[x] weaker than ch[y]
                    if cont(ch[x]) - cont(ch[y]) > 15: bad.append((v, name, ch[x], '>', ch[y], cont(ch[x]), cont(ch[y])))
        for ch in high:
            ch = [h for h in ch if live(h)]
            for k in range(1, len(ch) - 1):
                c = cont(ch[k])
                if c < cont(ch[k - 1]) - 15 and c < cont(ch[k + 1]) - 15:
                    bad.append((v, name, ch[k], 'dip', cont(ch[k - 1]), c, cont(ch[k + 1])))
print(json.dumps(stats), 'violations', len(bad))
for b in bad[:40]: print(b)
sys.exit(1 if bad else 0)
