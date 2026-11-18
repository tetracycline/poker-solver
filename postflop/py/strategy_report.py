"""Audit reachable combo strategies and summarize actions by hand/board buckets.

Input: pfdriver JSON. Output: compact CSV with per-node action probabilities
and conditional fold/call/raise thresholds. Aggregates only hands with
positive weighted reach. This is a decision table, not an inferred Nash solution.
"""
import argparse
import csv
import itertools
import json
from collections import defaultdict

RANKS = "23456789TJQKA"
GROUPS = ("two_pair_plus", "top_pair_good", "top_pair_weak",
          "middle_low_pair", "strong_draw", "weak_draw", "air")


def cards(s):
    if len(s) % 2:
        raise ValueError("odd card string")
    a = [s[i:i + 2] for i in range(0, len(s), 2)]
    if any(len(c) != 2 or c[0] not in RANKS or c[1] not in "cdhs" for c in a):
        raise ValueError("invalid cards")
    if len(a) != len(set(a)):
        raise ValueError("duplicate cards")
    return a


def board_bucket(board):
    b = cards(board)
    rs = [RANKS.index(c[0]) for c in b[:3]]
    suits = [c[1] for c in b[:3]]
    mx = max(rs)
    high = ("A_high" if mx == 12 else "KQ_high" if mx >= 10 else
            "JT_high" if mx >= 8 else "low_9")
    tags = [high]
    if len(set(rs)) < 3:
        tags.append("paired")
    if len(set(suits)) == 1:
        tags.append("monotone")
    return tags


def five_rank(cs):
    rs = sorted((RANKS.index(c[0]) + 2 for c in cs), reverse=True)
    from collections import Counter
    groups = sorted(((n, r) for r, n in Counter(rs).items()), reverse=True)
    flush = len(set(c[1] for c in cs)) == 1
    uniq = sorted(set(rs), reverse=True)
    if 14 in uniq:
        uniq.append(1)
    straight = next((v for v in uniq if all(v - k in uniq for k in range(5))), 0)
    if flush and straight:
        return (8, straight)
    if groups[0][0] == 4:
        return (7, groups[0][1], groups[1][1])
    if groups[0][0] == 3 and groups[1][0] >= 2:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *rs)
    if straight:
        return (4, straight)
    if groups[0][0] == 3:
        return (3, groups[0][1], *sorted((r for r in rs if r != groups[0][1]), reverse=True)[:2])
    if groups[0][0] == 2 and groups[1][0] == 2:
        hi, lo = sorted((groups[0][1], groups[1][1]), reverse=True)
        return (2, hi, lo, max(r for r in rs if r not in (hi, lo)))
    if groups[0][0] == 2:
        return (1, groups[0][1], *sorted((r for r in rs if r != groups[0][1]), reverse=True)[:3])
    return (0, *rs)


def has_straight_draw(cs):
    rs = {RANKS.index(c[0]) + 2 for c in cs}
    if 14 in rs:
        rs.add(1)
    completions = [r for r in range(2, 15)
                   if r not in rs and any(all(q in (rs | {r}) for q in range(hi - 4, hi + 1))
                                          for hi in range(5, 15))]
    return len(completions)


def hand_group(board, hand):
    b = cards(board)
    h = cards(hand)
    if set(b) & set(h):
        return None  # impossible private combo
    all_cards = b + h
    made = max(five_rank(c) for c in itertools.combinations(all_cards, 5))
    if made[0] >= 2:
        return GROUPS[0]
    top = max(RANKS.index(c[0]) for c in b)
    hr = [RANKS.index(c[0]) for c in h]
    br = [RANKS.index(c[0]) for c in b]
    if made[0] == 1:
        if top in hr and hr.count(top) == 1:
            kicker = max(x for x in hr if x != top)
            return GROUPS[1] if kicker >= 9 else GROUPS[2]  # J+ kicker
        return GROUPS[3]
    if len(b) < 5:
        suit_count = {s: sum(c[1] == s for c in all_cards) for s in "cdhs"}
        fd = any(n == 4 and any(c[1] == s for c in h) for s, n in suit_count.items())
        sd = has_straight_draw(all_cards) if len(b) == 3 else 0
        if fd or sd >= 2:
            return GROUPS[4]
        if sd == 1 or any(n == 3 and any(c[1] == s for c in h) for s, n in suit_count.items()):
            return GROUPS[5]
    return GROUPS[6]


def summarize(data, min_reach=1e-8):
    hands = data["hands"]
    rows, issues = [], []
    bykey = {(n["board"], n["line"]): n for n in data["nodes"]}
    for n in data["nodes"]:
        p = n["player"]
        nh = len(hands[p])
        actions = n["acts"]
        if len(n["strat"]) != nh * len(actions):
            issues.append(f"{n['line']}: strategy shape invalid")
            continue
        if len(n["w"][p]) != nh:
            issues.append(f"{n['line']}: reach shape invalid")
            continue
        # Relative parent check: a hand with zero parental reach cannot
        # reappear within a street, even if absolute weights get renormalized.
        for (b, line), ancestor in bykey.items():
            if b != n["board"] or not line or not n["line"].startswith(line + " "):
                continue
            for h, weight in enumerate(n["w"][p]):
                if weight > min_reach and ancestor["w"][p][h] <= min_reach:
                    issues.append(f"{n['line']}: unreachable hand {hands[p][h]} from {line}")
        buckets = defaultdict(lambda: [0.0] * len(actions))
        counts = defaultdict(float)
        for i, hand in enumerate(hands[p]):
            weight = n["w"][p][i]
            if weight <= min_reach:
                continue
            kind = hand_group(n["board"], hand)
            if kind is None:
                issues.append(f"{n['line']}: blocked combo {hand}")
                continue
            probs = [n["strat"][a * nh + i] for a in range(len(actions))]
            if any(x < -1e-6 or x > 1.000001 for x in probs) or abs(sum(probs) - 1) > .025:
                issues.append(f"{n['line']}: invalid strategy for {hand}")
                continue
            counts[kind] += weight
            for a, prob in enumerate(probs):
                buckets[kind][a] += weight * prob
        for kind in GROUPS:
            den = counts[kind]
            if den <= min_reach:
                continue
            values = [round(v / den, 6) for v in buckets[kind]]
            split = {k: sum(v for act, v in zip(actions, values) if act[0] in initials)
                     for k, initials in (("fold", "f"), ("call", "c"), ("raise", "ra"))}
            # Facing a bet: add fold, call, raise/all-in frequency as threshold estimates.
            for texture in board_bucket(n["board"]):
                for action, value in zip(actions, values):
                    rows.append(dict(board=n["board"], texture=texture, line=n["line"],
                                     hand_class=kind, action=action, frequency=value,
                                     reach_weight=round(den, 6), player=p,
                                     fold_frequency=round(split["fold"], 6),
                                     call_frequency=round(split["call"], 6),
                                     raise_frequency=round(split["raise"], 6)))
    return rows, sorted(set(issues))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("--output", required=True)
    p.add_argument("--audit", required=True)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    with open(args.input, encoding="utf8") as f:
        obj = json.load(f)
    rows, issues = summarize(obj)
    with open(args.output, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=["board", "texture", "line", "hand_class",
                                         "action", "frequency", "reach_weight", "player",
                                         "fold_frequency", "call_frequency", "raise_frequency"])
        w.writeheader()
        w.writerows(rows)
    with open(args.audit, "w", encoding="utf8") as f:
        json.dump({"rows": len(rows), "reach_issues": issues, "gto_expl_pct":
                   obj.get("info", {}).get("gto_expl_pct"),
                   "gto_converged": obj.get("info", {}).get("gto_converged")},
                  f, indent=2)
    if issues and args.strict:
        raise SystemExit(f"{len(issues)} reach/strategy validation failures")


if __name__ == "__main__":
    main()
