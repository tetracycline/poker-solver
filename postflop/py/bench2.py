"""Sensitivity of flop c-bet to the later-street abstraction: richer turn/river sizes + 4bb rake cap (GTO Gecko's setup)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from job import make_job, run
d = f'{PFDIR}/out/bench'
for fl in sys.argv[1].split(','):
    fo = f'{d}/{fl}_rich.json'
    if os.path.exists(fo): continue
    j = make_job('BTN_BB', 'gto', fl, fo + '.tmp', extract=[dict(prefix=[], street=True)], compress=True, target=0.3)
    j.update(turn_oop='33%,75%', turn_ip='33%,75%', turn_raise='3x,a', river_oop='33%,75%,a', river_ip='33%,75%,a', river_raise='a', rake_cap=400)
    run(j, f'{d}/{fl}_rich.job.json'); os.rename(fo + '.tmp', fo); print(fl, 'ok', flush=True)
