"""Map a node line (tokens x/bNN/c/f/r/a, streets split by '/') to a drill category, given which side was the preflop raiser."""
AGG = ('b', 'r', 'a')
def toks(line):
    st = line.split('/'); return [s.split() if s else [] for s in st]
def last_aggr(street_toks):
    # player (0 OOP / 1 IP) who bet/raised last on a street, or None
    p = None
    for i, t in enumerate(street_toks):
        if t[0] in AGG: p = i % 2
    return p
def category(line, player, pfr):
    """pfr: 0 if OOP raised preflop, 1 if IP. returns (key) or None"""
    S = toks(line); k = len(S) - 1; cur = S[-1]; prev = S[:-1]
    me_pfr = player == pfr
    facing = bool(cur) and cur[-1][0] in AGG
    nraise = sum(1 for t in cur if t[0] in AGG)
    if nraise >= 2: return 'vs_raise' if facing else None
    if facing and any(t[0] in AGG for t in cur[:-1]): return None
    if nraise == 1 and facing:
        # first bet of the street faced
        bettor = 1 - player
        my_bet_before = any(t[0] in AGG and i % 2 == player for i, t in enumerate(cur))
        if my_bet_before: return 'vs_raise'
        if k == 0: return 'f_vs_cbet' if not me_pfr else 'f_vs_bet_after_x'
        if k == 1:
            fl = last_aggr(S[0])
            if fl is None: return 'vs_delay' if not me_pfr else 'vs_probe'
            return 'vs_barrel' if fl == bettor else 'vs_turn_lead'
        if k == 2:
            return 'r_vs_bet'
    if facing: return None
    # first-in-street decision (check or bet available) — only if nobody bet yet this street
    if nraise: return None
    if k == 0:
        if me_pfr: return 'f_cbet'
        return 'f_float' if player == 1 else None  # OOP caller has no donk in this tree
    if k == 1:
        fl = last_aggr(S[0])
        if fl is None: return 'delay' if me_pfr else 'probe'
        if fl == player: return 'barrel'
        return 'stab'  # IP caller after the OOP aggressor checks the turn
    if k == 2:
        tl = last_aggr(S[1])
        if tl == player: return 'r_barrel'
        if tl is None: return 'r_stab'
        return None
CATS = [
    ('f_cbet', '翻牌 c-bet', 'flop'), ('f_vs_cbet', '面對翻牌 c-bet', 'flop'), ('f_float', '對手過牌後（翻牌）', 'flop'),
    ('f_vs_bet_after_x', '過牌後面對下注（翻牌）', 'flop'),
    ('barrel', '轉牌續打', 'turn'), ('vs_barrel', '面對轉牌續打', 'turn'), ('delay', '轉牌延遲 c-bet', 'turn'), ('vs_delay', '面對延遲 c-bet', 'turn'),
    ('probe', '轉牌主動下注（翻牌過牌過）', 'turn'), ('vs_probe', '面對轉牌探測', 'turn'), ('stab', '轉牌：對手放棄續打後', 'turn'), ('vs_turn_lead', '轉牌過牌後面對下注', 'turn'),
    ('r_barrel', '河牌三槍（價值／詐唬）', 'river'), ('r_stab', '河牌：轉牌過牌後', 'river'), ('r_vs_bet', '河牌抓詐（面對下注）', 'river'),
    ('vs_raise', '面對加注／全下', 'any'),
]
if __name__ == '__main__':
    T = [('x', 1), ('', 0), ('x b33', 0), ('x b33 r', 1), ('x b33 c/x', 1), ('x b33 c/x b50', 0), ('x x/', 0), ('x x/x', 1), ('x x/b50', 1), ('x x/x b50', 0),
         ('x b33 c/x b50 c/x', 1), ('x b33 c/x b50 c/x b75', 0), ('x b33 c/x x/', 0), ('x b33 c/x x/x', 1), ('x b33 c/x b50 a', 1)]
    for l, p in T: print(repr(l), p, category(l, p, 1))
    for l, p in [('', 0), ('b33', 1), ('x', 1), ('x b33', 0), ('b33 c/', 0), ('b33 c/x', 1), ('x x/', 0), ('x x/x', 1), ('x x/x b50', 0)]: print('oop-pfr', repr(l), p, category(l, p, 0))
