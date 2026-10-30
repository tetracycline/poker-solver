"""Charts + markdown tables for REPORT_postflop.md from report/validation.json (+ benchmark boards)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, glob, os, sys, statistics as stt, math
sys.path.insert(0, os.path.dirname(__file__))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from locks import wilson
REP = f'{PFDIR}/report'; V = json.load(open(f'{REP}/validation.json'))
for f in fm.findSystemFonts():
    if any(k in f for k in ('NotoSansCJK', 'NotoSansTC', 'WenQuanYi', 'Noto Sans CJK', 'DroidSansFallback')):
        fm.fontManager.addfont(f); plt.rcParams['font.family'] = fm.FontProperties(fname=f).get_name(); break
plt.rcParams.update({'figure.facecolor': '#0f1f17', 'axes.facecolor': '#14281d', 'text.color': '#e6efe9', 'axes.labelcolor': '#e6efe9',
                     'xtick.color': '#cfe0d5', 'ytick.color': '#cfe0d5', 'axes.edgecolor': '#3c5e4a'})
R = '23456789TJQKA'
def cls(fl):
    rs = sorted([R.index(fl[i]) for i in (0, 2, 4)], reverse=True); ns = len({fl[i + 1] for i in (0, 2, 4)})
    out = ['全部']
    out.append({12: 'A 高', 11: 'K 高'}.get(rs[0], 'Q/J/T 高' if rs[0] >= 8 else '9 以下'))
    out.append({1: '單色', 2: '兩色', 3: '彩虹'}[ns])
    nr = len(set(rs)); out.append('三條' if nr == 1 else '有對' if nr == 2 else '無對')
    if nr == 3: out.append('連張' if rs[0] - rs[2] <= 4 else '不連')
    return out
GECKO = {'全部': 46.6, 'A 高': 36.5, 'K 高': 58.3, 'Q/J/T 高': '45–50', '9 以下': 45.3, '彩虹': 53.5, '兩色': 43.7, '單色': 25.5, '有對': 57.9, '三條': 86.6, '連張': 40.2, '不連': 47.9}
GSMALL = {'全部': 27.8, '彩虹': 32.8, '兩色': 24.8, '單色': 19.9, '有對': 47.6, '三條': 45.6, '連張': 22.2}
def bytex(rows, key):
    g = {}
    for r in rows:
        if key not in r: continue
        for c in cls(r['flop']): g.setdefault(c, []).append(r[key])
    return {k: (stt.mean(v), len(v)) for k, v in g.items()}
md = []
# 1. c-bet by texture, BTN_BB
B = V['BTN_BB']; rows = B['rows']
cb, b33, xr = bytex(rows, 'cbet'), bytex(rows, 'b33'), bytex(rows, 'xr_b33')
order = ['全部', 'A 高', 'K 高', 'Q/J/T 高', '9 以下', '彩虹', '兩色', '單色', '無對', '有對', '三條', '連張', '不連']
md.append('| 牌面 | 翻牌數 | 本解 c-bet | 本解 33% | GTO Gecko c-bet | Gecko 33% | 本解 BB 過牌加注 vs 33% |\n|---|---|---|---|---|---|---|')
for k in order:
    if k not in cb: continue
    md.append(f"| {k} | {cb[k][1]} | {cb[k][0]:.1f}% | {b33[k][0]:.1f}% | {GECKO.get(k, '–')}{'%' if isinstance(GECKO.get(k), float) else ''} | {GSMALL.get(k, '–')}{'%' if k in GSMALL else ''} | {xr.get(k, (float('nan'),))[0]:.1f}% |")
T1 = '\n'.join(md); md = []
ks = [k for k in order if k in cb and isinstance(GECKO.get(k), float)]
fig, ax = plt.subplots(figsize=(10, 4.2)); x = range(len(ks))
ax.bar([i - .2 for i in x], [cb[k][0] for k in ks], .4, label='本解 (pfdriver)', color='#3fb27f')
ax.bar([i + .2 for i in x], [GECKO[k] for k in ks], .4, label='GTO Gecko (PioSolver, 1755 翻牌)', color='#c9a227')
ax.set_xticks(list(x)); ax.set_xticklabels(ks); ax.set_ylabel('BTN c-bet %'); ax.legend(facecolor='#14281d'); ax.set_title('BTN vs BB SRP：c-bet 頻率依牌面')
fig.tight_layout(); fig.savefig(f'{REP}/cbet_texture.png', dpi=110); plt.close(fig)
# 2. per spot summary
md.append('| 局面 | 翻牌數 | c-bet | 33% | 75% | 對手過牌加注 vs 33% | 對手棄牌 vs 33% | 過牌加注 vs 75% | 對手棄牌 vs 75% | 翻牌可剝削度 中位/最大 (%底池) |\n|---|---|---|---|---|---|---|---|---|---|')
for sp, S in V.items():
    g = lambda k: S[k].get('全部', [float('nan')])[0] if S.get(k) else float('nan')
    e = [x for x in S['expl'] if x is not None]
    md.append(f"| {sp} | {S['n']} | {g('cbet'):.1f}% | {g('b33'):.1f}% | {g('b75'):.1f}% | {g('xr33'):.1f}% | {g('fold33'):.1f}% | {g('xr75'):.1f}% | {g('fold75'):.1f}% | {stt.median(e):.2f} / {max(e):.2f} |")
T2 = '\n'.join(md); md = []
# 3. exploitability distribution
fig, ax = plt.subplots(figsize=(8, 3.6))
fl = [x for S in V.values() for x in S['expl'] if x is not None]; sub = [x for S in V.values() for x in S.get('sub_expl', []) if x is not None]
gap = [x for S in V.values() for x in S['exploit']['gap'] if x is not None]; sgap = [x for S in V.values() for x in S.get('sub_gap', []) if x is not None]
ax.hist([fl, sub, gap, sgap], bins=20, label=[f'GTO 翻牌 (n={len(fl)})', f'GTO 轉牌子樹 (n={len(sub)})', f'剝削 翻牌 hero gap (n={len(gap)})', f'剝削 子樹 hero gap (n={len(sgap)})'],
        color=['#3fb27f', '#7fd1a8', '#c9a227', '#e8d27a'])
ax.axvline(0.5, color='#e05555', ls='--'); ax.set_xlabel('% 底池'); ax.set_ylabel('解數'); ax.legend(facecolor='#14281d', fontsize=8); ax.set_title('收斂度：可剝削度 / 對鎖定對手的最佳回應差距')
fig.tight_layout(); fig.savefig(f'{REP}/exploitability.png', dpi=110); plt.close(fig)
def q(v, p): v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))] if v else float('nan')
T3 = '| 解 | 數量 | 中位 | p90 | 最大 |\n|---|---|---|---|---|\n' + '\n'.join(f'| {n} | {len(v)} | {q(v,.5):.3f}% | {q(v,.9):.3f}% | {max(v):.3f}% |' for n, v in (('GTO 翻牌樹', fl), ('GTO 轉牌子樹', sub), ('剝削 翻牌樹 (hero gap)', gap), ('剝削 轉牌子樹 (hero gap)', sgap)) if v)
# 4. monotonicity
T4 = ''
for sp in ('BTN_BB',):
    m = V.get(sp, {}).get('mono')
    if not m: continue
    T4 += f'\n**{sp}（GTO）面對下注時「繼續率」對「勝率」**\n\n| 街 | 節點 | Spearman ρ 中位 | ρ p10 | 勝率十分位 0–10…90–100% 的繼續率 |\n|---|---|---|---|---|\n'
    for st in ('flop', 'turn', 'river'):
        d = m[st]; T4 += f"| {st} | {d['nodes']} | {d['rho_median']:.2f} | {d['rho_p10']:.2f} | {' / '.join('–' if x is None else f'{x:.0f}' for x in d['deciles'])} |\n"
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for st, c in (('flop', '#3fb27f'), ('turn', '#c9a227'), ('river', '#e8d27a')):
        ax.plot([5 + 10 * i for i in range(10)], [x if x is not None else float('nan') for x in m[st]['deciles']], marker='o', color=c, label=st)
    ax.set_xlabel('組合對對手範圍的勝率 (%)'); ax.set_ylabel('繼續 (跟注+加注) %'); ax.legend(facecolor='#14281d'); ax.set_title('BTN vs BB：牌力單調性')
    fig.tight_layout(); fig.savefig(f'{REP}/monotonic.png', dpi=110); plt.close(fig)
T4 += '\n**所有局面：面對下注時繼續率 vs 勝率的 Spearman ρ（節點中位數）與河牌違規率**\n\n| 局面 | 版本 | 翻牌 ρ | 轉牌 ρ | 河牌 ρ | 河牌違規（組合） |\n|---|---|---|---|---|---|\n'
for sp, S in V.items():
    for vn, m in [('GTO', S.get('mono'))] + [(('剝削 你IP' if k == 'exp_ip' else '剝削 你OOP'), x) for k, x in (S.get('mono_exp') or {}).items()]:
        if not m: continue
        r = lambda st: '–' if m[st]['rho_median'] is None else f"{m[st]['rho_median']:.2f}"
        v = m['river']['violations']
        T4 += f"| {sp} | {vn} | {r('flop')} | {r('turn')} | {r('river')} | {v[0]:,} / {v[1]:,}（{100*v[0]/max(1,v[1]):.2f}%） |\n"
T4 += '\n河牌違規 = 勝率高 ≥20 個百分點的組合卻少繼續 ≥50 個百分點。\n'
# 4b. cross-sizing consistency
T9 = ''
if os.path.exists(f'{REP}/consistency.json'):
    CJ = json.load(open(f'{REP}/consistency.json'))
    T9 = '| 局面 | 版本 | 同一決策點的尺寸配對 | 範圍層級矛盾（面對大注棄牌反而較少） | 組合層級矛盾（面對大注繼續率高 ≥50pp） |\n|---|---|---|---|---|\n'
    for k, x in CJ.items():
        sp, v = k.split('|'); vn = {'gto': 'GTO', 'exp_ip': '剝削 你IP', 'exp_oop': '剝削 你OOP'}[v]
        T9 += f"| {sp} | {vn} | {x['pairs']:,} | {x['range_bad']:,}（{100*x['range_bad']/max(1,x['pairs']):.2f}%） | {x['combo_bad']:,} / {x['combos']:,}（加權 {x['combo_bad_w_pct']:.2f}%） |\n"
# 5. no-rake comparison
md.append('| 局面 | 翻牌數 | c-bet 有抽水 | c-bet 無抽水 | 33% 有/無 | 過牌加注 vs33 有/無 | 棄牌 vs33 有/無 |\n|---|---|---|---|---|---|---|')
for sp, S in V.items():
    N = S.get('norake')
    if not N: continue
    fls = {r['flop'] for r in N['rows']}; rk = [r for r in S['rows'] if r['flop'] in fls]
    m = lambda rows, k: stt.mean(r[k] for r in rows if k in r)
    md.append(f"| {sp} | {len(fls)} | {m(rk,'cbet'):.1f}% | {m(N['rows'],'cbet'):.1f}% | {m(rk,'b33'):.1f} / {m(N['rows'],'b33'):.1f}% | {m(rk,'xr_b33'):.1f} / {m(N['rows'],'xr_b33'):.1f}% | {m(rk,'fold_b33'):.1f} / {m(N['rows'],'fold_b33'):.1f}% |")
T5 = '\n'.join(md); md = []
# 6. exploit gains + locks
md.append('| 局面 | 你的位置 | 翻牌數 | 剝削 EV 增益 vs 用 GTO 打池子 (bb/手，平均) | 最小 / 最大 |\n|---|---|---|---|---|')
gains = {}
for sp, S in V.items():
    for side, key in (('IP', 'gain_ip'), ('OOP', 'gain_oop')):
        v = S['exploit'][key]
        if v: md.append(f'| {sp} | {side} | {len(v)} | {stt.mean(v):+.3f} | {min(v):+.3f} / {max(v):+.3f} |'); gains[f'{sp} {side}'] = stt.mean(v)
T6 = '\n'.join(md); md = []
if gains:
    fig, ax = plt.subplots(figsize=(8, 3.6)); ks = list(gains)
    ax.barh(ks, [gains[k] for k in ks], color='#c9a227'); ax.set_xlabel('bb / 到達翻牌的底池'); ax.set_title('剝削版比 GTO 版多賺（對 NL2 池鎖定策略）')
    fig.tight_layout(); fig.savefig(f'{REP}/exploit_gain.png', dpi=110); plt.close(fig)
# locks table: unique patterns per spot (first flop) with n + CI
seen = set(); md.append('| 局面 | 鎖定的對手節點 (regex) | 來源統計 | n | 目標 | 95% Wilson CI |\n|---|---|---|---|---|---|')
for sp, S in V.items():
    for ver, L in (S['exploit']['locks'] or {}).items():
        for x in L or []:
            src = x['src'].split(' + texture')[0]; k = (sp, ver, x['pat'])
            if k in seen: continue
            seen.add(k)
            if 'bet' in x and x.get('bet') is not None: t = f"下注 {100*x['bet']:.1f}%"; lo, hi = wilson(x['bet'], x['n'])
            else: t = f"棄牌 {100*x['fold']:.1f}%・加注 {100*x['raise_']:.1f}%"; lo, hi = wilson(x['fold'], x['n'])
            md.append(f"| {sp} {'(你IP)' if ver=='exp_ip' else '(你OOP)'} | `{x['pat']}` | {src}{'（+牌面調整）' if '+ texture' in x['src'] else ''} | {x['n']:,} | {t} | {100*lo:.1f}–{100*hi:.1f}% |")
T7 = '\n'.join(md)
# benchmark boards
BM = {'Ks7h2d': (82.9, 70.0), 'As7h2d': (40.0, 35.0), 'Ks8s3s': (27.7, None), '8s8h3d': (76.5, None)}
t8 = ['| 翻牌 | 本解 c-bet (33% / 75%) | GTO Gecko c-bet (33%) |\n|---|---|---|']
for fl, (g, gs) in BM.items():
    f = f'{PFDIR}/out/bench/{fl}.json'
    if not os.path.exists(f): continue
    from validate import freqs
    fr = json.load(open(f)); x = freqs(fr, 'x')
    t8.append(f"| {fl} | {x['b33']+x['b75']:.1f}% ({x['b33']:.1f} / {x['b75']:.1f}) | {g}%{f' ({gs})' if gs else ''} |")
T8 = '\n'.join(t8)
json.dump(dict(T1=T1, T2=T2, T3=T3, T4=T4, T5=T5, T6=T6, T7=T7, T8=T8, T9=T9), open(f'{REP}/tables.json', 'w'), ensure_ascii=False, indent=1)
print(T1); print(T2); print(T3); print(T4); print(T5); print(T6); print(T8); print(T7[:1500])
