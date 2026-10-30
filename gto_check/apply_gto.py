#!/usr/bin/env python3
"""Apply GTO-check verdicts to the trainer data (single source: preview site *.orig.js -> learn_data.js / reads_data.js).
Adds one short line `gl` ("GTO 約 x%，玩家池 y%") per answer; reverts rules whose pool deviation is not significant
(or points the other way) to the GTO action. Optional arg: extra output dir (live repo) to copy the two data files to."""
import json, sys, os, re, shutil
P = '/workspace/poker_mb/preview_3bet_iso_lines/site'
C = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/data/gto_check.json'))
def load(fn):
    s = open(f'{P}/{fn}').read(); return s
pc = lambda x: f'{round(100 * x)}%'
# ---------- learn_data
s = load('learn_data.orig.js'); pre = s[:s.index('{')]; LD = json.loads(s[s.index('{'):s.rindex('}') + 1]); post = s[s.rindex('}') + 1:]
R = {(e['tab'], e.get('id') or (e.get('read'), e.get('grp'))): e for e in C['rules'] if e['tab'] != 'rd'}
for k, t in LD['tb'].items():
    e = R[('tb', f"{t['o']}>{t['h']}")]
    t['gl'] = f"GTO：被 3-bet 約棄 {pc(e['gto_f3'])}、4-bet {pc(e['gto_4b'])}；玩家池棄 {pc(e['pool_f3'])}、4-bet {pc(e['pool_4b'])}"
    t['gv'] = e['v']
for k, t in LD['iso'].items():
    t['gl'] = f"GTO 不跛入，沒有理論值可比；玩家池跛入者被加注只棄 {t['lf']}%"
    t['gv'] = 'nonode'
LN = {e['id']: e for e in C['rules'] if e['tab'] == 'ln'}
SZ = {'ip_xr_big': '他過牌加注', 'ip_turn_xr': '他轉牌過牌加注', 'ip_probe': '他轉牌探測', 'ip_riv_small': '他河牌下注',
      'bb_cb_small': '他的 c-bet', 'bb_barrel2': '他轉牌下注', 'bb_barrel3': '他河牌大注', '3c_cbet': '他的 c-bet'}
nrev = 0
for r in LD['rules']:
    e = LN[r['id']]
    if e.get('claim'):
        cz = e['claim_zh']
        if e['claim'] in SZ: cz = SZ[e['claim']] + ' ' + cz.replace('占比', '占')
        r['gl'] = f"{cz}：GTO 約 {pc(e['gto_ref'])}，玩家池 {pc(e['pool'])}"
    r['gv'] = e['v']
    if e['v'] in ('ns', 'ns_dir') and r['dev']:
        r['orig'] = {'ans': r['ans'], 'why': r['why']}
        r['ans'] = r['gto']; r['ans_zh'] = r['gto_zh']; r['dev'] = False; r['ok'] = [x for x in r.get('ok', []) if x != r['gto']]
        r['why'] = '玩家池跟 GTO 差不多 → 照 GTO 打' if e['v'] == 'ns' else '玩家池偏的方向不支持剝削 → 照 GTO 打'
        nrev += 1
LD['gto_check'] = C['summary']
open(f'{P}/learn_data.js', 'w').write(pre + json.dumps(LD, ensure_ascii=False, separators=(',', ':')) + post)
# ---------- reads
s = load('reads_data.orig.js')
m = re.search(r'LD\.reads=(\[.*?\]);', s, re.S); reads = json.loads(m.group(1))
RD = {(e['read'], e['grp']): e for e in C['rules'] if e['tab'] == 'rd'}
RO = C['reads']
STZ = {'兩對以上占比': '兩對以上占', '空氣占比': '空氣占', '對手棄牌率': '他面對下注棄牌'}
for r in reads:
    o = RO[r['id']]
    if o['verdict'] == 'nonode': r['gl'] = f"解算器沒有這條線（{o['note']}）→ 只用玩家池資料"
    else: r['gl'] = f"{STZ[o['stat']]}：GTO 約 {pc(o['gto'])}，玩家池 {pc(o['pool'])}"
    for h in r['hands']:
        e = RD.get((r['id'], h['g']))
        if not e: continue
        h['gv'] = e['v']
        if e['v'] in ('ns', 'ns_dir') and e.get('gto_act'):
            h['orig'] = h['act']; ga = e['gto_act']
            h['act'] = '邊緣' if ga.startswith('邊緣') else ga
            if r['kind'] == 'dec' and h['act'] == '下注': h['act'] = '下注（價值）' if h['g'] in 'SM' else '下注（詐唬）'
            h['gn'] = '照 GTO 打（玩家池這裡偏得不明顯）'; nrev += 1
s2 = s[:m.start(1)] + json.dumps(reads, ensure_ascii=False, separators=(',', ':')) + s[m.end(1):]
open(f'{P}/reads_data.js', 'w').write(s2)
print('reverted', nrev)
for d in sys.argv[1:]:
    for fn in ('learn_data.js', 'reads_data.js'): shutil.copy(f'{P}/{fn}', f'{d}/{fn}')
