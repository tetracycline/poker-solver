#!/usr/bin/env python3
"""Parse NL2 6-handed hands that reach the flop heads-up into compact records for hand reading.
record: dict(t=spot type SRP/3BP/ISO/LMP, pa=aggressor pos, pc=caller pos, ip='A'|'C', bd=board str, ac=[(street,role,act,x,allin)],
             ha=holecards A or '', hc=holecards C or '', stk=eff stack bb, pot=flop pot bb)
act: x check, b bet (x = bet/pot before), c call, r raise (x = raise-to / facing-to), f fold."""
import sys, os, re, glob, pickle
from multiprocessing import Pool
POS = ['SB', 'BB', 'UTG', 'HJ', 'CO', 'BTN']; ORD = {p: i for i, p in enumerate(POS)}
RACT = re.compile(r'^(.+?): (folds|checks|calls|bets|raises)(?: \$([\d.]+))?(?: to \$([\d.]+))?(.*)$')
RSHOW = re.compile(r'^(.+?): shows \[(\w\w) (\w\w)\]')
RSUM = re.compile(r'^Seat \d+: (.+?) (?:\((?:button|small blind|big blind)\) )*(?:showed|mucked) \[(\w\w) (\w\w)\]')
def hand(L):
    if '($0.01/$0.02)' not in L[0]: return None
    bb = 0.02
    mb = re.search(r'Seat #(\d+) is the button', L[1]); btn = int(mb.group(1))
    seats = {}; i = 2
    while L[i].startswith('Seat '):
        m = re.match(r'Seat (\d+): (.+) \(\$([\d.]+) in chips\)', L[i]); seats[m.group(2)] = (int(m.group(1)), float(m.group(3)) / bb); i += 1
    if len(seats) != 6: return None
    order = sorted(seats, key=lambda n: (seats[n][0] - btn - 1) % 10)
    pos = {n: POS[k] for k, n in enumerate(order)}
    st = 0; acts = [[], [], [], []]; board = ''; shown = {}; posts = 0
    for ln in L[i:]:
        if ln.startswith('***'):
            if 'FIRST' in ln or 'SECOND' in ln: return None
            if ln.startswith('*** FLOP'): st = 1; board = ''.join(re.findall(r'\[([^\]]*)\]', ln)[0].split())
            elif ln.startswith('*** TURN'): st = 2; board += re.findall(r'\[([^\]]*)\]', ln)[-1].strip()
            elif ln.startswith('*** RIVER'): st = 3; board += re.findall(r'\[([^\]]*)\]', ln)[-1].strip()
            elif ln.startswith('*** SHOWDOWN'): st = 4
            continue
        if ': posts ' in ln:
            posts += 1
            if 'small blind' not in ln and 'big blind' not in ln: return None
            continue
        s = RSHOW.match(ln)
        if s: shown[s.group(1)] = s.group(2) + s.group(3); continue
        s = RSUM.match(ln)
        if s: shown.setdefault(s.group(1), s.group(2) + s.group(3)); continue
        if st == 4: continue
        a = RACT.match(ln)
        if a: acts[st].append((a.group(1), {'folds': 'f', 'checks': 'k', 'calls': 'c', 'bets': 'b', 'raises': 'r'}[a.group(2)], float(a.group(3) or 0) / bb, float(a.group(4) or 0) / bb, 'all-in' in a.group(5)))
    if st == 0 or not acts[1] and len(board) < 6: return None
    if posts != 2: return None
    # preflop
    contrib = {n: 0.0 for n in seats}; contrib[order[0]] = 0.5; contrib[order[1]] = 1.0
    folded = set(); raises = 0; limpers = []; raisers = []; callers_after = {}
    for (n, v, x, to, ai) in acts[0]:
        if v == 'f': folded.add(n)
        elif v == 'r': raises += 1; raisers.append(n); contrib[n] = to
        elif v == 'c':
            contrib[n] += x
            if raises == 0: limpers.append(n)
            else: callers_after.setdefault(raises, []).append(n)
    live = [n for n in seats if n not in folded]
    if len(live) != 2: return None
    pot = sum(contrib.values())
    if raises == 0:
        t = 'LMP'; A, C = sorted(live, key=lambda n: ORD[pos[n]])  # A = OOP
    elif raises == 1:
        A = raisers[0]; C = [n for n in live if n != A][0]
        if A not in live: return None
        t = 'ISO' if limpers else 'SRP'
        if t == 'ISO' and C not in limpers: return None
    elif raises == 2:
        if limpers: return None
        A = raisers[1]; C = [n for n in live if n != A]
        if A not in live or not C or C[0] != raisers[0]: return None
        C = C[0]; t = '3BP'
    else: return None
    role = {A: 'A', C: 'C'}
    ip = 'A' if ORD[pos[A]] > ORD[pos[C]] else 'C'
    stk = min(seats[A][1], seats[C][1])
    out = []; p = pot
    for s in (1, 2, 3):
        cur = {A: 0.0, C: 0.0}; facing = 0.0
        for (n, v, x, to, ai) in acts[s]:
            if n not in role: continue
            r = role[n]
            if v == 'k': out.append((s, r, 'x', 0, ai))
            elif v == 'b': out.append((s, r, 'b', round(x / p, 3), ai)); cur[n] = x; facing = x
            elif v == 'r': out.append((s, r, 'r', round(to / facing, 2) if facing else 0, ai)); cur[n] = to; facing = to
            elif v == 'c': out.append((s, r, 'c', 0, ai)); cur[n] += x
            elif v == 'f': out.append((s, r, 'f', 0, ai))
        p += sum(cur.values())
    return dict(t=t, pa=pos[A], pc=pos[C], ip=ip, bd=board, ac=out, ha=shown.get(A, ''), hc=shown.get(C, ''), stk=round(stk), pot=round(pot, 2))
def work(path):
    recs = []; buf = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for ln in f:
            ln = ln.rstrip('\n')
            if ln.startswith('Poker Hand #'):
                if buf and any(l.startswith('*** FLOP') for l in buf):
                    try:
                        r = hand(buf)
                        if r: recs.append(r)
                    except Exception: pass
                buf = [ln]
            elif ln: buf.append(ln)
        if buf and any(l.startswith('*** FLOP') for l in buf):
            try:
                r = hand(buf)
                if r: recs.append(r)
            except Exception: pass
    return recs
if __name__ == '__main__':
    os.nice(19)
    files = sorted(glob.glob('/workspace/poker/hhdealer/raw/*_NL2_*/*.txt'))
    if len(sys.argv) > 1: files = files[:int(sys.argv[1])]
    allr = []
    with Pool(2) as pool:
        for k, r in enumerate(pool.imap_unordered(work, files, chunksize=4)):
            allr += r
            if k % 50 == 0: print(k, len(files), len(allr), flush=True)
    pickle.dump(allr, open('data/hu.pkl' if len(sys.argv) == 1 else 'data/hu_test.pkl', 'wb'))
    from collections import Counter
    print('records', len(allr), Counter(r['t'] for r in allr), 'sd both', sum(1 for r in allr if r['ha'] and r['hc']), 'any', sum(1 for r in allr if r['ha'] or r['hc']))
