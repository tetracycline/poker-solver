"""Hand class of a 2-card holding on a 3-5 card board (beginner buckets) + flop texture."""
RK = '23456789TJQKA'; RV = {r: i for i, r in enumerate(RK)}
HC = ['strong', 'top_good', 'top_weak', 'mid_low', 'draw', 'weak_draw', 'air']
HC_ZH = {'strong': '兩對以上', 'top_good': '超對/頂對好踢', 'top_weak': '頂對弱踢', 'mid_low': '中小對', 'draw': '強聽牌', 'weak_draw': '卡順/兩高張', 'air': '空氣'}
def _straight(ranks):
    s = set(ranks)
    if 12 in s: s = s | {-1}
    for hi in range(12, 2, -1):
        if all((hi - k) in s for k in range(5)): return hi
    return None
def _has_straight_using(hole, board):
    rb = [RV[c[0]] for c in board]; rh = [RV[c[0]] for c in hole]
    a = _straight(rb + rh); b = _straight(rb)
    return a is not None and (b is None or a > b)
def _oesd(hole, board):
    rs = set(RV[c[0]] for c in hole + board); rb = set(RV[c[0]] for c in board); rh = set(RV[c[0]] for c in hole)
    ext = rs | ({-1} if 12 in rs else set())
    best = 0
    for lo in range(-1, 10):
        win = set(range(lo, lo + 4))
        if win <= ext and (win & (rh | ({-1} if 12 in rh else set()))):
            if lo - 1 >= -1 and lo + 4 <= 12: best = max(best, 2)
            else: best = max(best, 1)
    # gutshot: 4 of 5 consecutive
    gut = False
    for lo in range(-1, 9):
        win = set(range(lo, lo + 5))
        if len(win & ext) == 4 and (win & (rh | ({-1} if 12 in rh else set()))): gut = True
    return best == 2, gut
def hand_class(hole, board):
    """hole: 'AhKd' style 4 chars; board: string of 2-char cards"""
    h = [hole[0:2], hole[2:4]]; b = [board[i:i + 2] for i in range(0, len(board), 2)]
    allc = h + b; suits = [c[1] for c in allc]
    for s in set(suits):
        if suits.count(s) >= 5 and any(c[1] == s for c in h): return 'strong'
    if _has_straight_using(h, b): return 'strong'
    rb = [RV[c[0]] for c in b]; rh = [RV[c[0]] for c in h]
    from collections import Counter
    cb = Counter(rb)
    ub = sorted(set(rb), reverse=True)
    pocket = rh[0] == rh[1]
    hits = [r for r in rh if r in cb]
    if pocket and rh[0] in cb: return 'strong'                       # set / quads
    if any(cb[r] >= 2 for r in hits): return 'strong'                 # trips
    if len(set(hits)) == 2: return 'strong'                           # two pair with both hole cards
    river = len(b) == 5
    fd = any(suits.count(s) == 4 and any(c[1] == s for c in h) for s in set(suits)) and not river
    oe, gut = _oesd(h, b) if not river else (False, False)
    if pocket:
        if rh[0] > ub[0]: return 'top_good'
        return 'mid_low'
    if hits:
        r = hits[0]; k = [x for x in rh if x != r][0] if len(rh) == 2 else 0
        if r == ub[0]:
            good = k >= RV['T'] or (r == RV['A'] and k >= RV['9']) or (r >= RV['K'] and k >= RV['J'])
            return 'top_good' if good else 'top_weak'
        return 'mid_low'
    if fd or oe: return 'draw'
    if gut or (min(rh) > ub[0]): return 'weak_draw'
    return 'air'
TX = ['A_high', 'KQ_high', 'mid_high', 'low', 'paired', 'mono']
TX_ZH = {'A_high': 'A 高面', 'KQ_high': 'K/Q 高面', 'mid_high': 'J/T 高中張面', 'low': '低牌面(9 以下)', 'paired': '對子面', 'mono': '單色面'}
def texture(flop):
    c = [flop[i:i + 2] for i in range(0, 6, 2)]; r = sorted([RV[x[0]] for x in c], reverse=True); s = [x[1] for x in c]
    if len(set(s)) == 1: return 'mono'
    if len(set(r)) < 3: return 'paired'
    if r[0] == 12: return 'A_high'
    if r[0] >= 10: return 'KQ_high'
    if r[0] >= 8: return 'mid_high'
    return 'low'
def turn_type(flop, turn):
    """turn card type vs flop: 'over' (new highest), 'flush' (3rd of a suit on board), 'pair' (pairs board), 'blank'"""
    c = [flop[i:i + 2] for i in range(0, 6, 2)]; rs = [RV[x[0]] for x in c]; ss = [x[1] for x in c]
    if ss.count(turn[1]) >= 2: return 'flush'
    if RV[turn[0]] in rs: return 'pair'
    if RV[turn[0]] > max(rs): return 'over'
    return 'blank'
if __name__ == '__main__':
    for h, b in [('AhKd', 'Ks7c2d'), ('9h8h', 'Th7h2c'), ('QsQd', 'Js5c2d'), ('5h5d', 'Js5c2d'), ('Ah2h', 'Kh7h2c'), ('6d5c', '8s7c2d'), ('KdQc', '9s7c2d'), ('3d4c', '9s7c2dAs8h'), ('Kd7c', 'Ks7c2d'), ('Ad5d', 'Ac9c4h'), ('Jh9c', 'Kc9d2s')]:
        print(h, b, hand_class(h, b))
    for f in ['Ah7c2d', 'Ks8h3c', 'Th9c4s', '7s6d4c', '8s8d3c', 'Kh8h3h']: print(f, texture(f))
