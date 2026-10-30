#!/usr/bin/env python3
"""Extract GTO reference stats from postflop solver outputs (read-only, nice 19).
Per spot x flop: for every node, key=(player 'OOP'/'IP', coarse line) ->
  m: reach mass at node, a: {coarse act: mass}, g: {coarse act: {group S/M/W/D/A: mass}}
Mass normalised by flop root mass; turn-subtree nodes / #turn cards solved for that line, river nodes / #rivers.
Coarse tokens = same alphabet as the pool parser: x c f r bS(<=55%) bB(<=120%) bO(>120% or all-in lead)."""
import os, sys, json, glob, pickle
from collections import defaultdict
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, '/workspace/outputs/poker_solver/read_v1')
from vclass import fine, GROUP
OUT = '/workspace/postflop/out'
SPOTS = {'BTN_BB': 'SRP', 'CO_BB': 'SRP', 'HJ_BB': 'SRP', 'UTG_BB': 'SRP', 'SB3_BTN': '3BP', 'BB3_BTN': '3BP'}
def ctok(a, facing):
    if a in ('x', 'c', 'f', 'r'): return a
    if a == 'a': return 'r' if facing else 'bO'
    if a.startswith('b'):
        v = int(a[1:]); return 'bS' if v <= 55 else 'bB' if v <= 120 else 'bO'
    return a
def coarse(line):
    out = []
    for st in line.split('/'):
        facing = False; toks = []
        for a in st.split():
            toks.append(ctok(a, facing)); facing = a not in ('x', 'c', 'f')
        out.append(' '.join(toks))
    return '/'.join(out)
def facing_now(line):
    st = line.split('/')[-1].split()
    return bool(st) and st[-1] not in ('x', 'c', 'f')
def proc_file(path, rootmass, scale, acc, gcache):
    d = json.load(open(path)); H = d['hands']
    nriv = max(1, len(d.get('rivers', []) or []))
    for n in d['nodes']:
        p = n['player']; acts = n['acts']; nh = len(H[p]); line = n['line']; bd = n['board']
        w = np.asarray(n['w'][p], dtype=float)
        if w.sum() <= 0: continue
        s = np.asarray(n['strat'], dtype=float).reshape(len(acts), nh)
        sc = scale / rootmass * (1.0 / nriv if len(bd) == 10 else 1.0)
        key = ('OOP' if p == 0 else 'IP', coarse(line))
        e = acc[key]; e['m'] += w.sum() * sc
        ck = (p, bd, len(H[p]), H[p][0], H[p][-1])
        if ck not in gcache:
            gcache[ck] = np.array(['SMWDA'.index(GROUP[fine(h, bd)]) for h in H[p]])
        gi = gcache[ck]; fc = facing_now(line)
        for k, a in enumerate(acts):
            t = ctok(a, fc); m = w * s[k] * sc
            e['a'][t] += m.sum()
            gs = np.bincount(gi, weights=m, minlength=5)
            for j, G in enumerate('SMWDA'): e['g'][t][G] += gs[j]
def one(args):
    spot, fpath = args
    flop = os.path.basename(fpath)[:-5]; dr = os.path.dirname(fpath)
    acc = defaultdict(lambda: {'m': 0.0, 'a': defaultdict(float), 'g': defaultdict(lambda: defaultdict(float))})
    gcache = {}
    try:
        d = json.load(open(fpath)); root = d['nodes'][0]; rootmass = float(sum(root['w'][0]))
        del d
        # flop file: flop nodes only
        d = json.load(open(fpath)); H = d['hands']
        tmp = dict(nodes=[n for n in d['nodes'] if '/' not in n['line']], hands=H)
        del d
        proc_mem(tmp, rootmass, acc, gcache)
        subs = sorted(glob.glob(os.path.join(dr, flop + '_*.json')))
        bylin = defaultdict(list)
        for sp in subs:
            parts = os.path.basename(sp)[:-5].split('_')
            if len(parts) != 3 or '.' in parts[2]: continue
            bylin[parts[1]].append(sp)
        for lin, fs in bylin.items():
            for sp in fs: proc_file(sp, rootmass, 1.0 / len(fs), acc, gcache)
    except Exception as ex:
        import traceback; return spot, flop, {"err": traceback.format_exc()}
    res = {k: {'m': v['m'], 'a': dict(v['a']), 'g': {a: dict(g) for a, g in v['g'].items()}} for k, v in acc.items()}
    return spot, flop, res
def proc_mem(d, rootmass, acc, gcache):
    H = d['hands']
    for n in d['nodes']:
        p = n['player']; acts = n['acts']; nh = len(H[p]); line = n['line']; bd = n['board']
        w = np.asarray(n['w'][p], dtype=float)
        if w.sum() <= 0: continue
        s = np.asarray(n['strat'], dtype=float).reshape(len(acts), nh)
        sc = 1.0 / rootmass
        key = ('OOP' if p == 0 else 'IP', coarse(line)); e = acc[key]; e['m'] += w.sum() * sc
        ck = (p, bd, len(H[p]), H[p][0], H[p][-1])
        if ck not in gcache: gcache[ck] = np.array(['SMWDA'.index(GROUP[fine(h, bd)]) for h in H[p]])
        gi = gcache[ck]; fc = facing_now(line)
        for k, a in enumerate(acts):
            t = ctok(a, fc); m = w * s[k] * sc
            e['a'][t] += m.sum()
            gs = np.bincount(gi, weights=m, minlength=5)
            for j, G in enumerate('SMWDA'): e['g'][t][G] += gs[j]
if __name__ == '__main__':
    os.nice(19)
    jobs = []
    for spot in SPOTS:
        for f in sorted(glob.glob(f'{OUT}/{spot}/gto/*.json')):
            b = os.path.basename(f)
            if '_' in b or b.endswith('.job.json') or b.endswith('.v2plan.json'): continue
            jobs.append((spot, f))
    print(len(jobs), 'flop files', flush=True)
    res = defaultdict(dict); errs = 0
    with Pool(int(os.environ.get('NP', '2'))) as pool:
        for i, (spot, flop, r) in enumerate(pool.imap_unordered(one, jobs)):
            if 'err' in r: errs += 1; print('ERR', spot, flop, r['err'], flush=True); continue
            res[spot][flop] = r
            if i % 20 == 0: print(i, spot, flop, flush=True)
    pickle.dump({'spots': SPOTS, 'data': dict(res)}, open('data/gto_flops.pkl', 'wb'))
    print('done', {s: len(v) for s, v in res.items()}, 'errs', errs)
