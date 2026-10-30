import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, subprocess, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from ranges import SPOTS, ranges, to_str
DRV = f'{PFDIR}/pfdriver/target/release/pfdriver'
RAKE = 0.05; CAP_BB = 10.0
def tree_cfg(spot):
    s = SPOTS[spot]; pfr = s['pfr']
    # coarse full-flop tree (turn/river refined later by turn subgame re-solves)
    c = dict(flop_ip='33%,75%', flop_raise='3x,a', turn_oop='66%', turn_ip='66%', turn_raise='a',
             river_oop='75%', river_ip='75%', river_raise='a', turn_donk='', river_donk='')
    c['flop_oop'] = '33%,75%' if pfr == 'oop' else ''
    return c
SUB = dict(turn_oop='50%,100%', turn_ip='50%,100%', turn_raise='a', river_oop='50%,100%,a', river_ip='50%,100%,a', river_raise='a', turn_donk='', river_donk='')
def make_job(spot, ver, flop, out, iters=1000, target=0.5, extract=None, locks=None, rank=1.5, compress=False):
    s = SPOTS[spot]; wo, wi = ranges(spot, ver)
    j = dict(flop=flop, pot=int(round(s['pot'] * 100)), stack=int(round(s['stack'] * 100)), rake_rate=0.0 if ver == 'norake' else RAKE, rake_cap=CAP_BB * 100,
             oop=to_str(wo), ip=to_str(wi), iters=iters, target_pct=target, out=out, extract=extract or [], compress=compress)
    j.update(tree_cfg(spot))
    if ver not in ('gto', 'norake'):
        j['hero'] = 1 if ver == 'exp_ip' else 0; j['locks'] = locks or []; j['rank_pct'] = rank
    return j
def run(job, jobfile):
    json.dump(job, open(jobfile, 'w'))
    p = subprocess.run([DRV, jobfile], capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-2000:])
    return p.stderr
if __name__ == '__main__':
    spot, ver, flop = sys.argv[1:4]
    os.makedirs(f'{PFDIR}/tmp', exist_ok=True)
    j = make_job(spot, ver, flop, f'{PFDIR}/tmp/{spot}_{ver}_{flop}.json', extract=[dict(prefix=[], street=True)])
    print(run(j, f'{PFDIR}/tmp/job.json'))
