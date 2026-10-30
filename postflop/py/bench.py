"""Benchmark boards published by GTO Gecko (PioSolver, BTN vs BB SRP 100bb, 5% rake cap 4bb, sizes 33%/75%, no donk)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from job import make_job, run
d = f'{PFDIR}/out/bench'; os.makedirs(d, exist_ok=True)
for fl in sys.argv[1].split(','):
    fo = f'{d}/{fl}.json'
    if os.path.exists(fo): continue
    j = make_job('BTN_BB', 'gto', fl, fo + '.tmp', extract=[dict(prefix=[], street=True)], compress=True, target=0.3)
    run(j, f'{d}/{fl}.job.json'); os.rename(fo + '.tmp', fo); print(fl, 'ok', flush=True)
