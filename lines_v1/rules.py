#!/usr/bin/env python3
"""Turn aggregated solver buckets into beginner rules: one action + one short WHY line.
rec = blend 65% pool-exploit (EXP) + 35% GTO (robust vs the max-exploit being brittle); 'dev' when rec != GTO majority."""
import json
from handclass import HC, HC_ZH, TX, TX_ZH
A = json.load(open('data/lines_agg.json'))
WE, WG = 0.65, 0.35
NMIN = 80
SIZE = {'flop': ('33%', '75%'), 'turn': ('半池', '1 池'), 'river': ('半池', '1 池/全下')}
BETCATS = {'f_cbet', 'barrel', 'delay', 'probe', 'r_barrel', 'r_stab', 'stab'}
def get(ver, g, d, c, hc):
    return A.get(f'{ver}|{g}|{d}|{c}|{hc}')
def decide(E, G, betnode):
    def bl(a): return WE * E.get(a, 0) + WG * G.get(a, 0)
    def gtoact(F):
        if betnode:
            pb = F.get('small', 0) + F.get('big', 0)
            if pb < 0.5: return 'x'
            return 'small' if F.get('small', 0) >= F.get('big', 0) else 'big'
        r = F.get('r', 0); f = F.get('f', 0); c = F.get('c', 0)
        if r >= 0.4: return 'r'
        return 'f' if f > c + r else 'c'
    if betnode:
        pb = bl('small') + bl('big'); px = bl('x')
        if px >= pb: rec = 'x'
        else: rec = 'small' if bl('small') >= bl('big') else 'big'
        ok = [a for a in ('x', 'small', 'big') if a != rec and bl(a) >= 0.33]
    else:
        r, f, c = bl('r'), bl('f'), bl('c')
        rec = 'r' if r >= 0.4 else ('f' if f > c + r else 'c')
        ok = [a for a in ('f', 'c', 'r') if a != rec and bl(a) >= 0.33]
    return rec, gtoact(G), ok, {a: round(bl(a), 2) for a in (('x', 'small', 'big') if betnode else ('f', 'c', 'r'))}
LBL = {'x': '過牌', 'f': '棄牌', 'c': '跟注', 'r': '加注'}
def label(a, st):
    if a in LBL: return LBL[a]
    return '下注 ' + (SIZE[st][0] if a == 'small' else SIZE[st][1])
TXF = {'A_high': 50.5, 'KQ_high': 49.2, 'mid_high': 42.7, 'low': 41.4, 'paired': 55, 'mono': 50}
VAL = ('strong', 'top_good'); MID = ('top_weak', 'mid_low'); BL = ('draw', 'weak_draw', 'air')
def why(g, c, a, hc, tx, st):
    if g == 'SRP_IP' and c == 'f_cbet':
        tf = TXF.get(tx, 47)
        if a == 'big':
            if hc in VAL: return '你領先很多；池面對 75% 仍跟 40% → 大注收最多'
            if hc == 'draw': return '池面對 75% 棄 55%，被跟也有 1/3 勝率'
            return f'池面對 75% c-bet 棄 55%（保本 43%）→ 直接賺'
        if a == 'small':
            if hc in VAL: return '池面對 33% 只棄 39%、跟 53% → 小注讓差牌付錢'
            return f'33% 只要 25% 棄牌就回本，這種面池棄 {tf:.0f}%'
        if hc in VAL: return '這面 BB 擊中多，慢打控池，轉牌再收'
        if hc in MID: return '有攤牌價值，下注只被更好的牌跟 → 過牌'
        return '這面 BB 擊中多（GTO 也過），轉牌延遲下注池棄 58%'
    if g == 'SRP_IP' and c == 'barrel':
        if a == 'x':
            if hc in MID: return '有攤牌價值；轉牌被加注 64% 是兩對+ → 過牌'
            return '轉牌續打池只棄 41%，空氣不划算 → 放棄'
        if hc in VAL: return '翻牌跟注的多是中對/聽牌 → 轉牌繼續收價值'
        if hc in MID: return '翻牌跟注範圍很寬（弱對/聽牌多）→ 半池薄價值'
        if a == 'small': return '轉牌半池只要 33% 棄牌，池棄 36%＋你的補牌'
        return '轉牌 1 池池棄 50%，加上補牌勝率才有利潤'
    if g == 'SRP_IP' and c == 'delay':
        if a == 'x': return '中等牌過牌攤牌，不用逼走更差的牌' if hc in MID else '這張轉牌對 BB 有利 → 過牌'
        if hc in VAL: return '翻牌過牌讓對手以為你弱 → 轉牌收價值'
        if hc in MID: return '翻牌過、轉牌下注池棄 58% → 中等牌也直接拿走底池'
        return '翻牌過、轉牌下注：池棄 58% → 最好偷的時機'
    if g == 'SRP_IP' and c == 'r_barrel':
        if a == 'big': return '河牌池跟注寬（面對 1 池仍跟 38%）→ 大注收價值' if hc in VAL else '河牌 1 池保本 50%，池棄 57%'
        if a == 'small': return '薄價值用半池：池面對半池跟 48%' if hc in VAL + MID else '河牌半池保本 33%，池棄 43%'
        if hc in MID: return '中等牌下注只會被更好的牌跟 → 過牌攤牌'
        if hc in VAL: return '這張河牌對手強牌變多 → 過牌攤牌'
        return '第三槍池只棄約 40%，詐唬幾乎不賺 → 放棄'
    if g == 'SRP_IP' and c == 'r_stab':
        if a in ('big', 'small'):
            if hc in VAL: return '對手兩條街都過牌＝弱 → 河牌收價值'
            if hc in MID: return '對手兩條街都過牌＝弱 → 半池薄價值'
            return '翻轉都過後河牌下 ~1 池，池棄 75%（最佳詐唬點）'
        return '有攤牌價值，過牌免費看牌' if hc in MID else '過牌攤牌'
    if g == 'SRP_IP' and c == 'vs_probe':
        if a == 'f': return '池的轉牌探測空氣只占 11%，空氣跟不起'
        if a == 'r': return '強牌加注：池面對加注很少棄'
        return '探測範圍有很多弱對/聽牌（43%）→ 有對子就跟'
    if c == 'vs_raise':
        sfx = ' → 棄' if a == 'f' else ' → 你夠強，跟'
        if st == 'river': return '河牌加注幾乎都是強牌（空氣 8%、順子以上 52%）' + sfx
        if st == 'turn': return '轉牌加注只有 6% 空氣、兩對以上 64%' + sfx
        return '翻牌加注空氣只 12%、頂對以上 59%' + (' → 棄' if a == 'f' else ' → 有勝率就跟')
    if g == 'SRP_IP' and c == 'r_vs_bet' or g == 'SRP_BB' and c == 'r_vs_bet' or g == '3BP_caller' and c == 'r_vs_bet':
        if a == 'f': return '河牌下注空氣只約 18%，你只贏詐唬 → 棄'
        if a == 'r': return '河牌池跟加注不少 → 強牌加注收價值'
        return '河牌下注空氣約 18%＋弱對 18%，你贏這些 → 跟'
    if g == 'SRP_BB' and c == 'f_vs_cbet':
        if a == 'f': return '沒對子沒聽牌，跟了也很難贏 → 棄'
        if a == 'r':
            if hc in VAL: return '強牌加注：池面對加注只棄 41%，會付錢'
            return '聽牌加注：池棄 41%，被跟還有補牌'
        if hc in BL: return '池翻牌 c-bet 空氣占 24%，你的牌有勝率 → 跟'
        return '池 c-bet 空氣占 24% → 你的對子常常領先，跟'
    if g == 'SRP_BB' and c == 'vs_barrel':
        if a == 'f': return '轉牌下注空氣只 12%，你只贏詐唬 → 棄'
        if a == 'r': return '強牌加注收價值'
        return '池轉牌下注很寬（弱對+聽牌約 40%）→ 跟'
    if g == 'SRP_BB' and c == 'probe':
        if a == 'x': return '中等牌過牌攤牌就好' if hc in MID else '空氣下注也偷不到 → 過牌'
        if hc in VAL: return '對手翻牌沒 c-bet＝弱 → 轉牌主動收價值'
        return '對手翻牌放棄 c-bet，轉牌下注池棄 50%'
    if g == 'SRP_BB' and c == 'r_stab':
        if a in ('big', 'small'):
            if hc in VAL: return '轉牌對手過牌示弱 → 河牌收價值'
            if hc in MID: return '對手轉牌也不下注＝弱 → 半池薄價值'
            return '翻轉都過，河牌你先下 ~1 池：池棄 67%'
        return '有攤牌價值，過牌就好' if hc in MID else '過牌'
    if g == '3BP_3bettor' and c == 'f_cbet':
        if a == 'x': return '有攤牌價值，過牌控池' if hc in MID else '這面對手擊中多 → 過牌'
        if a == 'small': return '3bet 底池小注保本 25%，池棄 29%，價值牌也被跟'
        return '池面對 75% 棄 50%（保本 43%）'
    if g == '3BP_3bettor' and c == 'barrel':
        if a == 'x': return '轉牌池只棄 36%，SPR 低過牌也能攤牌' if hc in MID + VAL else '轉牌詐唬池不太棄 → 放棄'
        return '轉牌收價值，SPR 低可以直接打到全下' if hc in VAL else '半池保本 33%，池棄 36% ＋補牌'
    if g == '3BP_3bettor' and c == 'r_barrel':
        if a == 'x': return '3bet 底池 OOP 第三槍詐唬 EV≈0（池只棄 36%）' if hc in BL else '過牌攤牌'
        return '河牌收價值：池跟注寬'
    if g == '3BP_caller' and c == 'f_vs_cbet':
        if a == 'f': return '3bet 底池賠率差，沒牌就棄'
        if a == 'r': return '強牌加注'
        return '池 3bet 後 c-bet 67%，範圍很寬 → 有勝率就跟'
    if g == '3BP_caller' and c == 'vs_barrel':
        if a == 'f': return '轉牌再下注範圍變強 → 弱牌棄'
        return '你有位置、牌夠強 → 跟'
    return ''
CELLS = [('SRP_IP', 'f_cbet', 'tx', 'flop', '你開池、BB 跟注；翻牌 BB 過牌'),
         ('SRP_IP', 'barrel', 'all', 'turn', '翻牌 c-bet 被跟；轉牌 BB 過牌'),
         ('SRP_IP', 'delay', 'all', 'turn', '翻牌你也過牌；轉牌 BB 過牌'),
         ('SRP_IP', 'r_barrel', 'all', 'river', '翻、轉都下注被跟；河牌 BB 過牌'),
         ('SRP_IP', 'r_stab', 'all', 'river', '轉牌兩人都過牌；河牌 BB 過牌'),
         ('SRP_IP', 'vs_probe', 'all', 'turn', '翻牌你過牌；轉牌 BB 先下注'),
         ('SRP_IP', 'vs_raise', 'street', None, '你下注，BB 加注'),
         ('SRP_IP', 'r_vs_bet', 'all', 'river', '河牌 BB 先下注'),
         ('SRP_BB', 'f_vs_cbet', 'tx', 'flop', '你 BB 跟注；翻牌你過牌，對手 c-bet'),
         ('SRP_BB', 'vs_barrel', 'all', 'turn', '翻牌跟了 c-bet；轉牌對手再下注'),
         ('SRP_BB', 'probe', 'all', 'turn', '翻牌對手沒 c-bet；轉牌你先行動'),
         ('SRP_BB', 'r_vs_bet', 'all', 'river', '河牌你過牌，對手下注'),
         ('SRP_BB', 'r_stab', 'all', 'river', '轉牌兩人都過牌；河牌你先行動'),
         ('3BP_3bettor', 'f_cbet', 'all', 'flop', '你 3bet、BTN 跟注；翻牌你先行動'),
         ('3BP_3bettor', 'barrel', 'all', 'turn', '翻牌 c-bet 被跟；轉牌你先行動'),
         ('3BP_3bettor', 'r_barrel', 'all', 'river', '翻、轉都下注被跟；河牌你先行動'),
         ('3BP_caller', 'f_vs_cbet', 'all', 'flop', '你跟了 3bet（有位置）；翻牌對手 c-bet'),
         ('3BP_caller', 'vs_barrel', 'all', 'turn', '翻牌跟了；轉牌對手再下注'),
         ('3BP_caller', 'r_vs_bet', 'all', 'river', '河牌對手下注')]
GROUP_ZH = {'SRP_IP': '單加注底池・你開池（有位置）', 'SRP_BB': '單加注底池・你在 BB 防守', '3BP_3bettor': '3bet 底池・你 3bet（沒位置）', '3BP_caller': '3bet 底池・你跟 3bet（有位置）'}
rules = []
GTO_ONLY = {('SRP_IP', 'r_stab')}   # exploit tree barely reaches this line (n<50); GTO + pool river data instead
for g, c, dim, st0, sit in CELLS:
    dims = TX if dim == 'tx' else (['ST_flop', 'ST_turn', 'ST_river'] if dim == 'street' else ['ALL'])
    for d in dims:
        st = st0 or d[3:]
        for hc in HC:
            E = get('exp', g, d, c, hc); G = get('gto', g, d, c, hc); fb = False
            if dim == 'tx' and (not E or not G or E['n'] < NMIN or G['n'] < NMIN):
                E = get('exp', g, 'ALL', c, hc); G = get('gto', g, 'ALL', c, hc); fb = True
            if (g, c) in GTO_ONLY and G and G['n'] >= 40: E = G
            if not E or not G or E['n'] < 40 or G['n'] < 40: continue
            rec, gto, ok, bl = decide(E, G, c in BETCATS)
            r = dict(id=f'{g}|{c}|{d}|{hc}', group=g, group_zh=GROUP_ZH[g], cat=c, street=st, sit=sit + ('' if dim != 'street' else {'flop': '（翻牌）', 'turn': '（轉牌）', 'river': '（河牌）'}[st]),
                     tx=d if dim == 'tx' else None, tx_zh=TX_ZH.get(d) if dim == 'tx' else None, hc=hc, hc_zh=HC_ZH[hc],
                     ans=rec, ans_zh=label(rec, st), gto=gto, gto_zh=label(gto, st), ok=ok, dev=(rec != gto), blend=bl,
                     exp={k: v for k, v in E.items() if k != 'n'}, gto_f={k: v for k, v in G.items() if k != 'n'}, n=[E['n'], G['n']], fallback=fb,
                     why=why(g, c, rec, hc, d if dim == 'tx' else None, st), choices=['x', 'small', 'big'] if c in BETCATS else ['f', 'c', 'r'])
            # river 'after x-x' air: solver EXP n is tiny there -> pool river data decides (bet ~pot, fold 74.9%)
            if g == 'SRP_IP' and c == 'r_stab' and hc in ('air', 'weak_draw'):
                r.update(ans='big', ans_zh=label('big', st), dev=(r['gto'] != 'big'), why=why(g, c, 'big', hc, None, st), note='river_bluff.md: SRP IP 翻轉都過 fold 74.9% @90% pot (n=21,387)')
            if g == 'SRP_BB' and c == 'r_stab' and hc in ('air', 'weak_draw'):
                r.update(ans='big', ans_zh=label('big', st), dev=(r['gto'] != 'big'), why=why(g, c, 'big', hc, None, st), note='river_bluff.md: SRP OOP 翻轉都過 fold 66.9% @89% pot (n=34,825)')
            rules.append(r)
json.dump(rules, open('data/rules.json', 'w'), ensure_ascii=False, indent=0)
print(len(rules), 'rules;', sum(r['dev'] for r in rules), 'exploit deviations')
for r in rules:
    print(f"{r['group']:12s} {r['cat']:9s} {(r['tx'] or r['street']):8s} {r['hc']:9s} -> {r['ans_zh']:10s} GTO {r['gto_zh']:10s} {'★' if r['dev'] else ' '} {r['why']}")
