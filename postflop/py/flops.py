"""Representative flop subsets: all 1755 strategically distinct flops with their raw weights (22100 total),
sorted by texture key, then systematic sampling (equal cumulative-weight strata) -> each pick has weight 1/N."""
import itertools
R = '23456789TJQKA'; S = 'cdhs'
def canon(cards):
    # canonical by suit relabel; cards = [(r,s)]
    best = None
    for perm in itertools.permutations(range(4)):
        c = sorted([(r, perm[s]) for r, s in cards], reverse=True); t = tuple(c)
        if best is None or t < best: best = t
    return best
def all_flops():
    W = {}
    for combo in itertools.combinations([(r, s) for r in range(13) for s in range(4)], 3):
        k = canon(combo); W[k] = W.get(k, 0) + 1
    return W
def fstr(k):
    # choose natural suits: map canonical suit ids to s,h,d,c in order of appearance
    order = []; 
    for r, s in k:
        if s not in order: order.append(s)
    m = {s: 'shdc'[i] for i, s in enumerate(order)}
    return ''.join(R[r] + m[s] for r, s in k)
def feats(k):
    rs = sorted([r for r, _ in k], reverse=True); ns = len(set(s for _, s in k))
    suit = {1: 0, 2: 1, 3: 2}[ns]  # mono, twotone, rainbow
    paired = 0 if len(set(rs)) == 3 else 1 if len(set(rs)) == 2 else 2
    gaps = rs[0] - rs[2]
    return (rs[0], paired, suit, gaps, rs[1], rs[2])
def sample(n, offset=0.5):
    W = all_flops(); keys = sorted(W, key=feats, reverse=True); tot = sum(W.values())
    out = []; acc = 0; targets = [(i + offset) * tot / n for i in range(n)]; ti = 0
    for k in keys:
        lo, hi = acc, acc + W[k]; acc = hi
        while ti < n and targets[ti] < hi:
            out.append(fstr(k)); ti += 1
    return out
if __name__ == '__main__':
    W = all_flops(); print(len(W), sum(W.values()))
    for n in (30, 12, 10, 8): print(n, sample(n))
