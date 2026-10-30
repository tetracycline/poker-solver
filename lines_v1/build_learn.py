#!/usr/bin/env python3
"""Single source of truth for the learn page: 3-bet + iso + action lines -> learn_data.js"""
import json, subprocess, sys, os
H = os.path.dirname(os.path.abspath(__file__)); X = os.path.join(H, '../exploit_v3/data')
OUT = sys.argv[1] if len(sys.argv) > 1 else '/workspace/poker_mb/preview_3bet_iso_lines/site/learn_data.js'
TR = os.path.join(os.path.dirname(OUT), 'pf_data.js')
pf = json.loads(subprocess.check_output(['node', '-e', f"global.window={{}};require('{TR}');process.stdout.write(JSON.stringify({{names:window.PF.names,nodes:Object.fromEntries(Object.entries(window.PF.nodes).filter(([k])=>k.includes('open>')||k.endsWith('rfi')))}}))"]))
NAMES = pf['names']
pool = json.load(open('/workspace/poker/hhdealer/pool_stats.json'))
TB = json.load(open(f'{X}/threebet_ranges.json')); ISO = json.load(open(f'{X}/iso_ranges.json'))
R = json.load(open(f'{H}/data/rules.json')); EX = json.load(open(f'{H}/data/examples.json'))
ORDER = ['UTG', 'HJ', 'CO', 'BTN', 'SB', 'BB']
tb = {}
for sp, v in TB.items():
    o, h = sp.split('>'); node = pf['nodes'][f'{o}open>{h}']; ip = ORDER.index(h) > ORDER.index(o) and h not in ('SB', 'BB')
    gto = {NAMES[i]: s for i, s in enumerate(node['gto']['s'])} if 'gto' in node else {}
    vs4 = {}
    for k, a in v['vs4'].items():
        if k in ('AA', 'KK'): vs4[k] = 'jam'
        elif k == 'QQ': vs4[k] = a if a != 'fold' else 'fold'
        else: vs4[k] = 'fold'   # model jams with AQ/AJ only come from the GTO-locked jam node
    val = [k for k, a in v['range'].items() if a[0] == '3' and v['kind'][k] == 'value']
    semi = [k for k, a in v['range'].items() if a[0] == '3' and v['kind'][k] != 'value']
    call = [k for k, a in v['range'].items() if a == 'c']
    tb[sp] = dict(o=o, h=h, ip=ip, open=pf['nodes'][f'{o}rfi']['to']['open'], to=node['to']['3bet'], pf3=round(v['pfold3'] * 100), p4=round(v['p4'] * 100),
                  val=val, semi=semi, call=call, vs4=vs4, vs4_model=v['vs4'], eqc={k: round(e * 100) for k, e in v['eq_vs_call'].items()},
                  eq4={k: round(e * 100) for k, e in v['eq_vs_4b'].items()}, pct=v['pct'], gto=gto, oo=v['opener_open_pct'])
iso = {}
for sp, v in ISO.items():
    two = sp.endswith('_2limp'); base = sp.replace('_2limp', ''); l, h = base.split('>')
    ev = v['ev_iso_med']; core = [k for k in NAMES if v['act'].get(k) == 'iso' and ev.get(k, -9) >= 1.0]
    adv = [k for k in NAMES if v['act'].get(k) == 'iso' and k not in core]
    other = 'check' if h == 'BB' else ('limp' if h == 'SB' else 'fold')
    lim = [k for k in NAMES if v['act'].get(k) == 'limp'] if h == 'SB' else []
    iso[sp] = dict(l=l, h=h, two=two, size=v['size'], core=core, adv=adv, other=other, limp=lim, limp_pct=round(sum(6 if len(k) == 2 else 4 if k[-1] == 's' else 12 for k in lim) / 1326 * 100, 1),
                   lf=round(v['limper_fold'] * 100), lc=round(v['limper_call'] * 100), lr=round(v['limper_rr'] * 100, 1),
                   pct=round(sum(6 if len(k) == 2 else 4 if k[-1] == 's' else 12 for k in core) / 1326 * 100, 1))
ISO_POST = [
    dict(sit='iso 後只剩跛入者跟（單挑）', ans='照「你開池」那套打：翻牌 c-bet', why='跛入範圍比 BB 防守還弱，單挑 limp 底池面對下注棄 57%'),
    dict(sit='iso 後 2 人以上跟（多人）・沒中', ans='過牌放棄', why='多人底池 75% 下注只有 39% 拿下（保本要 43%）→ 不詐唬'),
    dict(sit='iso 後多人・頂對好踢以上', ans='下注 75%', why='多人時總有人用更差的牌跟 → 大注收價值'),
    dict(sit='iso 後多人・中小對/弱聽牌', ans='過牌', why='多人底池中等牌很難贏到攤牌，不要建大底池'),
    dict(sit='跛入者再加注（limp-raise）', ans='QQ+、AK 全下，其他棄', why='NL2 limp-raise 只有 2.5–4.6%，幾乎都是 AA/KK 陷阱'),
]
rules = []
RIV = {'weak_draw': '沒中・有高張', 'draw': '聽牌沒中'}
for r in R:
    if r['street'] == 'river' and r['hc'] in RIV: r['hc_zh'] = RIV[r['hc']]
    rules.append({k: r[k] for k in ('id', 'group', 'group_zh', 'cat', 'street', 'sit', 'tx', 'tx_zh', 'hc', 'hc_zh', 'ans', 'ans_zh', 'gto', 'gto_zh', 'ok', 'dev', 'why', 'choices')}
                 | dict(gf=r['gto_f'], ex=[[e['h'], e['b'], e['spot'], e['pot']] for e in EX.get(r['id'], [])]))
D = dict(ver='learn-preview-1031', tb=tb, iso=iso, iso_post=ISO_POST, rules=rules,
         pool=dict(f3=pool.get('meta', {}).get('n_hands')))
open(OUT, 'w').write('window.LD=' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('wrote', OUT, os.path.getsize(OUT), 'bytes;', len(tb), '3bet spots,', len(iso), 'iso spots,', len(rules), 'rules')
for sp in ('CO>BTN', 'BTN>BB', 'SB>BB'): print(sp, tb[sp]['val'], tb[sp]['semi'][:6], 'gto keys', len(tb[sp]['gto']))
for sp in ('UTG>BTN', 'SB>BB', 'UTG>BTN_2limp'): print(sp, iso[sp]['pct'], iso[sp]['core'][:12])
