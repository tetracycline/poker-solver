"""Starting ranges for postflop solves, taken from the v8 preflop data (single source of truth).
gto: both players use pf_data 'gto'.  exp-hero: hero uses pf_data 'exp' (exploit best response),
villain uses the NL2 pool model that the exp layer was solved against (exploit_rake.json pool_strat)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json
PF = json.load(open(f'{ROOTDIR}/v8_build/build/pf_data.json'))
EX = json.load(open(f'{ROOTDIR}/preflop/exploit_rake.json'))
NR = json.load(open(f'{ROOTDIR}/preflop/gto_norake.json'))  # no-rake GTO (validation only)
NAMES = PF['names']; ACTS = {k: v['acts'] for k, v in PF['nodes'].items()}
# spot: (oop seat, ip seat, [(node, action) chain for OOP], [... for IP], pot_bb, stack_bb, pfr)
SPOTS = {
 'BTN_BB': dict(oop='BB', ip='BTN', oopc=[('BTNopen>BB', 'call')], ipc=[('BTNrfi', 'open')], pot=5.5, stack=97.5, pfr='ip', kind='SRP'),
 'CO_BB':  dict(oop='BB', ip='CO',  oopc=[('COopen>BB', 'call')],  ipc=[('COrfi', 'open')],  pot=5.5, stack=97.5, pfr='ip', kind='SRP'),
 'SB_BB':  dict(oop='SB', ip='BB',  oopc=[('SBrfi', 'open')],      ipc=[('SBopen>BB', 'call')], pot=6.0, stack=97.0, pfr='oop', kind='SRP'),
 'UTG_BB': dict(oop='BB', ip='UTG', oopc=[('UTGopen>BB', 'call')], ipc=[('UTGrfi', 'open')], pot=5.5, stack=97.5, pfr='ip', kind='SRP'),
 'HJ_BB':  dict(oop='BB', ip='HJ',  oopc=[('HJopen>BB', 'call')],  ipc=[('HJrfi', 'open')],  pot=5.5, stack=97.5, pfr='ip', kind='SRP'),
 'SB3_BTN': dict(oop='SB', ip='BTN', oopc=[('BTNopen>SB', '3bet')], ipc=[('BTNrfi', 'open'), ('BTNopen>SB3b', 'call')], pot=21.0, stack=90.0, pfr='oop', kind='3BP'),
 'BB3_BTN': dict(oop='BB', ip='BTN', oopc=[('BTNopen>BB', '3bet')], ipc=[('BTNrfi', 'open'), ('BTNopen>BB3b', 'call')], pot=20.5, stack=90.0, pfr='oop', kind='3BP'),
}
def weights(chain, src):
    w = [1.0] * 169
    for node, act in chain:
        ai = ACTS[node].index(act)
        if src == 'pool': S = EX['pool_strat'][node]; f = [row[ai] for row in S]
        elif src == 'norake': ai = NR['nodes'][node]['acts'].index(act); f = [row[ai] for row in NR['nodes'][node]['strat']]
        else: S = PF['nodes'][node][src]['s']; f = [row[ai] / 100 for row in S]
        w = [a * b for a, b in zip(w, f)]
    return w
def to_str(w, thr=0.005):
    return ','.join(f'{n}:{min(1.0, x):.3f}' for n, x in zip(NAMES, w) if x >= thr)
def ranges(spot, ver):
    s = SPOTS[spot]
    if ver == 'gto': so, si = 'gto', 'gto'
    elif ver == 'norake': so, si = 'norake', 'norake'
    elif ver == 'exp_ip': so, si = 'pool', 'exp'
    elif ver == 'exp_oop': so, si = 'exp', 'pool'
    wo, wi = weights(s['oopc'], so), weights(s['ipc'], si)
    return wo, wi
def combos(w):
    return sum(x * (6 if len(n) == 2 else 4 if n[2] == 's' else 12) for n, x in zip(NAMES, w))
if __name__ == '__main__':
    for sp in SPOTS:
        for v in ['gto', 'exp_ip', 'exp_oop']:
            wo, wi = ranges(sp, v); print(sp, v, f'OOP {combos(wo):.0f} combos ({combos(wo)/13.26:.1f}%)  IP {combos(wi):.0f} ({combos(wi)/13.26:.1f}%)')
