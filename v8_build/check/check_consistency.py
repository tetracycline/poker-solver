"""Independent re-implementation of the grading rule on pf_data.js, compared with the chart cells the browser rendered
(chart_dump.json from test.js) and with PK.judge. Also counts the drill question pool."""
import os as _os
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _PRE=_os.path.join(_HERE,'..','..','preflop')
import json, re, sys
src = open(_os.path.join(_HERE,'..','out','pf_data.js')).read()
PF = json.loads(src[src.index('=') + 1:].rstrip().rstrip(';'))
N = PF['names']; IX = {n: i for i, n in enumerate(N)}
dump = json.load(open(sys.argv[1] if len(sys.argv) > 1 else _os.path.join(_HERE,'chart_dump.json')))
def ok(n, v, h):
    s = PF['nodes'][n][v]['s'][IX[h]]; A = PF['nodes'][n]['acts']; m = max(range(len(s)), key=lambda j: (s[j], -j))
    return [a for j, a in enumerate(A) if j == m or s[j] >= 25]
bad = 0; cells = 0
for v in ('exp', 'gto'):
    for n in PF['nodes']:
        d = dump[v + '|' + n]
        for h in N:
            cells += 1; mine = ','.join(ok(n, v, h))
            if d['cells'][h]['ok'] != mine or d['judge'][h] != mine: bad += 1; print('MISMATCH', v, n, h, mine, d['cells'][h]['ok'], d['judge'][h])
fam = lambda n: 'rfi' if n.endswith('rfi') else 'vsjam' if n.endswith('jam') else 'vs4b' if n.endswith('4b') else 'vs3b' if n.endswith('3b') else 'bbdef' if n.endswith('>BB') else 'sbdef' if n.endswith('>SB') else 'ipdef'
DR = {'bb-utg': ['UTGopen>BB'], 'bb-hj': ['HJopen>BB'], 'bb-co': ['COopen>BB'], 'bb-btn': ['BTNopen>BB'], 'bb-sb': ['SBopen>BB'],
      'rfi-utg': ['UTGrfi'], 'rfi-hj': ['HJrfi'], 'rfi-co': ['COrfi'], 'btn': ['BTNrfi'], 'rfi-sb': ['SBrfi']}
allN = list(PF['nodes'])
for k, f in [('open', ['rfi']), ('sb', ['sbdef']), ('3bet', ['ipdef']), ('vs3b', ['vs3b']), ('vs4b', ['vs4b', 'vsjam']), ('mix', None)]:
    DR[k] = [n for n in allN if f is None or fam(n) in f]
pool = {v: {d: sum(1 for n in ns for h in N if PF['nodes'][n][v]['r'][IX[h]] >= 25) for d, ns in DR.items()} for v in ('exp', 'gto')}
uniq = {v: pool[v]['mix'] for v in pool}
k6 = {v: (PF['nodes']['BTNopen>BB'][v]['s'][IX['K6o']], ok('BTNopen>BB', v, 'K6o')) for v in ('exp', 'gto')}
print(json.dumps({'cells_checked': cells, 'mismatches': bad, 'question_pool_per_drill': pool, 'unique_spots(node×hand)': uniq, 'K6o_BB_vs_BTN': k6}, ensure_ascii=False))
sys.exit(1 if bad else 0)
