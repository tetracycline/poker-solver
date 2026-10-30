import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, os, sys, time, random, traceback
sys.path.insert(0, os.path.dirname(__file__))
from job import make_job, run, SUB, tree_cfg
from ranges import SPOTS
from flops import sample
import locks as LK
OUT = f'{PFDIR}/out'
NFLOP = dict(BTN_BB=30, CO_BB=12, SB_BB=12, UTG_BB=8, HJ_BB=8, SB3_BTN=10, BB3_BTN=10)
OFFS = dict(BTN_BB=0.5, CO_BB=0.37, SB_BB=0.63, UTG_BB=0.3, HJ_BB=0.7, SB3_BTN=0.45, BB3_BTN=0.55)
DECK = [r + s for r in '23456789TJQKA' for s in 'cdhs']
def flops_for(spot): return sample(NFLOP[spot], OFFS[spot])
def turns_for(flop, k=3):
    rng = random.Random('t' + flop); rest = [c for c in DECK if c not in [flop[i:i+2] for i in (0, 2, 4)]]
    return rng.sample(rest, k)
def rivers_for(flop, turn, k=2):
    rng = random.Random('r' + flop + turn); rest = [c for c in DECK if c not in [flop[i:i+2] for i in (0, 2, 4)] + [turn]]
    return rng.sample(rest, k)
def flop_lines(spot):
    return (['x b33 c', 'x b75 c', 'x x'] if SPOTS[spot]['pfr'] == 'ip' else ['b33 c', 'b75 c', 'x x'])
TURN_LINES = ['x b50 c', 'x b100 c', 'x x', 'b50 c', 'b100 c']
def lock_list(spot, ver, flop):
    if ver == 'gto': return [], []
    s = SPOTS[spot]; hero_ip = ver == 'exp_ip'
    villain_is_pfr = (s['pfr'] == 'ip') != hero_ip
    L = LK.build(s['kind'], s['pfr'], villain_is_pfr, flop)
    return LK.driver_locks(L), L
def solve_flop(spot, ver, flop):
    d = f'{OUT}/{spot}/{ver}'; os.makedirs(d, exist_ok=True); fo = f'{d}/{flop}.json'
    if os.path.exists(fo): return json.load(open(fo))
    turns = turns_for(flop)
    ex = [dict(prefix=[], street=True)] + [dict(prefix=l.split() + [t], street=False, raw=True) for l in flop_lines(spot) for t in turns]
    dl, L = lock_list(spot, ver, flop)
    j = make_job(spot, ver, flop, fo + '.tmp', extract=ex, locks=dl, compress=True, target=0.5, rank=1.5)
    log = run(j, f'{d}/{flop}.job.json'); os.rename(fo + '.tmp', fo)
    r = json.load(open(fo)); r['info']['log'] = log; r['info']['locks'] = L; r['turns'] = turns
    json.dump(r, open(fo, 'w'), separators=(',', ':')); return r
def solve_sub(spot, ver, flop, fr, line, turn):
    d = f'{OUT}/{spot}/{ver}'; key = f"{flop}_{line.replace(' ', '')}_{turn}"; fo = f'{d}/{key}.json'
    if os.path.exists(fo): return
    H = fr['hands']; node = None
    for n in fr['nodes']:
        if n['line'] == line + '/' and n['board'][-2:] == turn: node = n; break
    if node is None: print('  no turn node', key); return
    wo = [(H[0][i], w) for i, w in enumerate(node['wr'][0]) if w > 1e-4]
    wi = [(H[1][i], w) for i, w in enumerate(node['wr'][1]) if w > 1e-4]
    pot = node['pot']; stack = fr['stack'] - node['bets'][0]
    rivers = rivers_for(flop, turn)
    ex = [dict(prefix=[], street=True)] + [dict(prefix=tl.split() + [rv], street=True) for tl in TURN_LINES for rv in rivers]
    dl, L = lock_list(spot, ver, flop)
    j = make_job(spot, ver, flop, fo + '.tmp', extract=ex, locks=dl, compress=False, target=0.3, rank=1.5)
    j.update(SUB); j.update(dict(oop='', ip='', oop_w=wo, ip_w=wi, turn=turn, pot=pot, stack=stack, line0=line.split() + ['/']))
    toks = line.split(); agg = [i for i, t in enumerate(toks) if t[0] in 'bra']
    j['root_no_bet'] = bool(agg) and agg[-1] % 2 == 1  # IP bet last -> no turn donk (matches the flop tree / NL2 lines)
    log = run(j, f'{d}/{key}.job.json'); os.rename(fo + '.tmp', fo)
    r = json.load(open(fo)); r['info']['log'] = log; r['line0'] = line; r['turn'] = turn; r['rivers'] = rivers
    json.dump(r, open(fo, 'w'), separators=(',', ':'))
def main_line(fr, spot):
    # bigger c-bet size at the PFR's first flop decision -> that line gets turn subgames
    H = fr['hands']; root = '' if SPOTS[spot]['pfr'] == 'oop' else 'x'
    for n in fr['nodes']:
        if n['line'] == root:
            p = n['player']; nh = len(H[p]); w = n['w'][p]; tw = sum(w) or 1
            fr_ = {a: sum(w[h] * n['strat'][i * nh + h] for h in range(nh)) / tw for i, a in enumerate(n['acts'])}
            return ('x ' if root == 'x' else '') + ('b33' if fr_.get('b33', 0) >= fr_.get('b75', 0) else 'b75') + ' c'
def do(spot, vers=('gto', 'exp_ip', 'exp_oop'), nmax=None):
    fl = flops_for(spot)[:nmax]
    for flop in fl:
        for ver in vers:
            t = time.time()
            try:
                fr = solve_flop(spot, ver, flop)
                ml = main_line(fr, spot)
                for line in [ml, 'x x']:
                    for turn in fr['turns'] if 'turns' in fr else turns_for(flop):
                        solve_sub(spot, ver, flop, fr, line, turn)
                print(f'{spot} {ver} {flop} ok {time.time()-t:.0f}s', flush=True)
            except Exception as e:
                print(f'{spot} {ver} {flop} FAIL {e}', flush=True); traceback.print_exc()
if __name__ == '__main__':
    spots = sys.argv[1].split(',') if len(sys.argv) > 1 else list(NFLOP)
    nmax = int(sys.argv[2]) if len(sys.argv) > 2 else None
    for sp in spots: do(sp, nmax=nmax)
