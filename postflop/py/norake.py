import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from job import make_job, run
from pipeline import flops_for
OUT = f'{PFDIR}/out'
for spot in sys.argv[1].split(','):
    d = f'{OUT}/{spot}/norake'; os.makedirs(d, exist_ok=True)
    for fl in flops_for(spot):
        fo = f'{d}/{fl}.json'
        if os.path.exists(fo): continue
        j = make_job(spot, 'norake', fl, fo + '.tmp', extract=[dict(prefix=[], street=True)], compress=True, target=0.5)
        run(j, f'{d}/{fl}.job.json'); os.rename(fo + '.tmp', fo); print(spot, fl, 'ok', flush=True)
