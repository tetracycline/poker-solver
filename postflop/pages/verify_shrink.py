"""Every node a question can come from (pr >= 0.002) must be byte-identical after shrinking; count askable combos both sides."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, glob, gzip
S = f'{PFDIR}/site/postflop/data'; D = f'{PFDIR}/pages/postflop/data'
same = diff = ask0 = ask1 = 0
def askable(n): us = set(n.get('u', [])) | set(n.get('uc', [])); return sum(1 for i, w in enumerate(n['w']) if w >= 10 and i not in us) if n['pr'] >= 0.002 else 0
for f in sorted(glob.glob(f'{S}/*/*.json')):
    A = json.load(open(f)); B = json.loads(gzip.open(f.replace(S, D) + '.gz').read())
    for v in A['v']:
        a = [n for n in A['v'][v] if n['pr'] >= 0.002]; b = B['v'][v]
        ask0 += sum(map(askable, A['v'][v])); ask1 += sum(map(askable, b))
        if json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True): same += 1
        else: diff += 1
print(f'versions-per-flop identical {same}, different {diff}; askable combos before {ask0:,} after {ask1:,}')
