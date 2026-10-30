#!/usr/bin/env python3
"""reads.json -> preview reads_data.js (讀牌 tab)."""
import json, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vclass import fine, GROUP, cards
random.seed(3)
D = json.load(open('data/reads.json'))
GRPN = {'ip': '你開池・BB 跟', 'bb': '你 BB 防守', '3b': '3-bet 底池', 'iso': '隔離跛入者'}
HZ = dict(S='兩對以上', M='頂對好踢 / 超對', W='弱對 / 頂對小踢', D='聽牌', A='空氣')
WHY = {
 'ip_donk': 'BB 先下注，兩對以上只 {S}%，多是弱對/聽牌 → 頂對就加注，空氣丟',
 'ip_xr_min': '最小加注不代表堅果：兩對以上 {S}%，弱對+空氣 {WA}% → 頂對跟，空氣丟',
 'ip_xr_big': '大加注才偏強：兩對以上 {S}%＋聽牌 {D}% → 頂對跟一條，弱對、空氣丟',
 'ip_xc_lead': '跟注後轉牌突然下注，兩對以上升到 {S}% → 頂對跟，空氣丟',
 'ip_probe': '你放過翻牌，他轉牌下注多是弱對/聽牌（強牌 {S}%）→ 頂對加注，弱對跟',
 'ip_turn_xr': '轉牌過牌加注 = {S}% 兩對以上，NL2 很少這樣詐唬 → 只有強牌續，弱對、聽牌丟',
 'ip_riv_small': '河牌小注很雜，弱對最多（{W}%）→ 弱對可以抓，空氣丟',
 'ip_riv_big': '河牌大注 {S}% 兩對以上，但仍有 {A}% 空氣 → 頂對跟，空氣丟',
 'ip_riv_over': '河牌超池 = {S}% 兩對以上，詐唬很少 → 頂對也丟',
 'ip_turn_dec': '他跟完又過牌：{G}% 之後會棄牌、強牌只 {S}% → 繼續下注；弱對過牌省錢',
 'ip_riv_dec': '他跟了兩條又過牌：被下注會棄 {f}% → 頂對以上下注、空氣可詐唬；弱對過牌',
 'bb_cb_small': '小 c-bet 很寬：空氣+後來棄牌 {AG}% → 弱對可跟，頂對以上可加注',
 'bb_cb_big': '大 c-bet 比較實：頂對以上 {SM}% → 頂對跟，弱對看情況，空氣丟',
 'bb_probe': '他翻牌不 c-bet = 幾乎沒強牌（{SM}%），下注會棄 {f}% → 轉牌直接下注',
 'bb_delay': '延遲 c-bet 多是弱對/空氣（{WA}%）→ 弱對跟，頂對以上加注',
 'bb_barrel2': '第二槍變強：頂對以上 {SM}% → 頂對跟，聽牌、空氣多半丟',
 'bb_barrel3': '三槍大注 = {S}% 兩對以上 → 只有兩對以上能跟，頂對多半輸',
 'bb_donk_raised': '你先下注被加注：頂對以上 {SM}% → 弱對丟，頂對跟',
 '3b_raised': '3-bet 底池被加注：頂對以上 {SM}% → 超對跟，弱對、空氣丟',
 '3b_riv_dec': '他跟兩條多是頂對/弱對，被下注只棄 {f}% → 只用頂對好踢以上下注，不詐唬',
 '3c_cbet': '3-bet 者 c-bet：頂對/超對 {M}%，空氣+放棄 {AG}% → 弱對也能跟，空氣丟',
 '3c_over': '翻牌超池/全下：超對 {M}% 或空氣 {A}%，很少兩對 → 頂對好踢以上跟',
 'iso_donk': '跛入者先下注多是弱對（{W}%），強牌只 {S}% → 頂對加注，弱對跟',
 'iso_xc_lead': '跛入者跟完轉牌突然下注：強牌 {S}%、弱對 {W}% → 頂對以上繼續，空氣丟',
 'iso_xr': '跛入者過牌加注：兩對以上 {S}% → 頂對跟，弱對丟',
 'iso_turn_dec': '跛入者跟完又過牌：多是弱對，下注只棄 {f}% → 用有牌的下注，空氣過牌',
}
def grp_of(i): return 'ip' if i.startswith('ip_') else 'bb' if i.startswith('bb_') else 'iso' if i.startswith('iso') else '3b'
def sample_hole(board, g):
    dk = [r + s for r in '23456789TJQKA' for s in 'shdc' if r + s not in cards(board)]
    for _ in range(4000):
        h = random.sample(dk, 2)
        if GROUP[fine(''.join(h), board)] == g:
            if g == 'A' and fine(''.join(h), board) != 'air' and random.random() < 0.7: continue
            return ''.join(h)
    return None
out = []
for r in D:
    p = {k: round(v * 100) for k, v in r['grp'].items()}
    vals = dict(S=p['S'], M=p['M'], W=p['W'], D=p['D'], A=p['A'], G=p['G'], SM=p['S'] + p['M'], WA=p['W'] + p['A'], AG=p['A'] + p['G'],
                f=round(r.get('resp', {}).get('fold', 0) * 100))
    hands = []
    for g in 'SMWDA':
        if g not in r['act']: continue
        c = sample_hole(r['board'], g)
        if not c: continue
        h = dict(g=g, zh=HZ[g], c=c, act=r['act'][g], eq=round(r['eq'][g] * 100))
        hands.append(h)
    out.append(dict(id=r['id'], grp=grp_of(r['id']), spot=r['spot'], line=r['line'], kind=r['kind'], street=r['street'], board=r['board'],
                    n=r['n'], nsd=r['nsd'], ess=r['ess'], bar=p, why=WHY[r['id']].format(**vals), hands=hands,
                    need=round(r.get('need', 0) * 100 + r.get('margin', 0) * 100) if r['kind'] == 'face' else None,
                    fold=vals['f'] if r['kind'] == 'dec' else None, small=r['ess'] < 120))
js = 'window.LD=window.LD||{};LD.reads=' + json.dumps(out, ensure_ascii=False) + ';LD.readGrp=' + json.dumps(GRPN, ensure_ascii=False) + ';'
open('/workspace/poker_mb/preview_3bet_iso_lines/site/reads_data.js', 'w').write(js)
json.dump(out, open('data/reads_trainer.json', 'w'), ensure_ascii=False, indent=1)
for o in out: print(o['id'], o['n'], o['nsd'], o['why'])
