import json, sys
from handclass import HC, TX
A = json.load(open('data/lines_agg.json'))
def row(ver, g, tx, c, hc):
    v = A.get(f'{ver}|{g}|{tx}|{c}|{hc}'); 
    if not v: return '   -   '
    acts = [a for a in ('x', 'small', 'big', 'f', 'c', 'r') if a in v]
    return ' '.join(f'{a[0]}{int(round(100*v[a])):>3}' for a in acts) + f' (n{int(v["n"])})'
g, c = sys.argv[1], sys.argv[2]; txs = sys.argv[3].split(',') if len(sys.argv) > 3 else ['ALL'] + TX
for tx in txs:
    print('==', g, c, tx)
    for hc in HC: print(f'  {hc:10s} GTO {row("gto", g, tx, c, hc):40s} EXP {row("exp", g, tx, c, hc)}')
