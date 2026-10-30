import json, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
    if os.path.exists(f): fm.fontManager.addfont(f); plt.rcParams['font.family'] = fm.FontProperties(fname=f).get_name()
F = json.load(open('final.json')); R = json.load(open('results.json')); N = R['names']; RK = '23456789TJQKA'
ix = {n: i for i, n in enumerate(N)}; BG = '#0f1a14'; TX = '#e8f5ec'
def cell(i, j):
    return RK[i] * 2 if i == j else (RK[i] + RK[j] + 's' if i > j else RK[j] + RK[i] + 'o')
def grid(ax, val, colors, title):
    ax.set_xlim(0, 13); ax.set_ylim(13, 0); ax.axis('off')
    for r in range(13):
        for c in range(13):
            n = cell(12 - r, 12 - c); v = val[ix[n]]
            ax.add_patch(Rectangle((c, r), 1, 1, color=colors(v), lw=0)); ax.add_patch(Rectangle((c, r), 1, 1, fill=False, ec=BG, lw=1))
            ax.text(c + .5, r + .55, n, ha='center', va='center', fontsize=9.5, color=TX if colors(v) in ('#24332a',) else '#08120c', fontweight='bold')
    ax.set_title(title, color=TX, fontsize=15, pad=8)
G1 = lambda v: '#3ecf7a' if v >= .5 else ('#8fdcae' if v > .05 else '#24332a')
EXC = lambda v: '#e0a23f' if v >= .5 else '#24332a'
def REC(v): return {2: '#3ecf7a', 1: '#c9e86a', 0: '#24332a'}[v]
seats = ['UTG', 'HJ', 'CO', 'BTN', 'SB']; ZH = {'UTG': 'UTG', 'HJ': 'HJ', 'CO': 'CO', 'BTN': 'BTN', 'SB': 'SB（對 BB）'}
def seat_fig(h, axs):
    f = F[h]; core = set(f['core_cells']); rec = set(f['rec_cells'])
    rv = [2 if n in core else 1 if n in rec else 0 for n in N]
    grid(axs[0], f['gto_open'], G1, f'{ZH[h]}  GTO {f["gto"]:.0f}%')
    grid(axs[1], [1.0 if d > 0 else 0 for d in f['dev_base']], EXC, f'{ZH[h]}  剝削（現行）{f["exploit"]:.0f}%')
    grid(axs[2], rv, REC, f'{ZH[h]}  建議 {f["rec"]:.0f}%（深綠=核心 {f["core"]:.0f}%）')
fig, axs = plt.subplots(5, 3, figsize=(21, 36), facecolor=BG)
for k, h in enumerate(seats): seat_fig(h, axs[k])
fig.suptitle('開池範圍：GTO（綠）／現行剝削（橘）／穩健建議（深綠=每個情境都賺，黃綠=大多數情境賺）', color=TX, fontsize=20, y=0.995)
plt.tight_layout(rect=(0, 0, 1, 0.99)); fig.savefig('rfi_grids_all.png', dpi=80, facecolor=BG); plt.close(fig)
for h in seats:
    fig, axs = plt.subplots(1, 3, figsize=(21, 7.6), facecolor=BG); seat_fig(h, axs)
    plt.tight_layout(); fig.savefig(f'rfi_grid_{h}.png', dpi=90, facecolor=BG); plt.close(fig)
# sensitivity chart
fig, ax = plt.subplots(figsize=(13, 7.5), facecolor=BG); ax.set_facecolor(BG)
xs = [0, 25, 50, 75, 100]; keys = ['base', 'a25', 'a50', 'a75', 'a100']; cols = {'UTG': '#8fb3ff', 'HJ': '#b48fff', 'CO': '#ffd36b', 'BTN': '#ff9d5c', 'SB': '#ff6b6b'}
for h in seats:
    ys = [R[h][k]['open'] * 100 for k in keys]; ax.plot(xs, ys, '-o', color=cols[h], lw=3, ms=8, label=f'{h}（GTO {F[h]["gto"]:.0f}%）')
    ax.axhline(F[h]['gto'], color=cols[h], ls=':', lw=1.5)
    ax.text(101, ys[-1], h, color=cols[h], fontsize=14, va='center')
ax.set_xlabel('對手棄牌/3bet 頻率往 GTO 靠攏的程度（0%=NL2 玩家池原樣，100%=GTO 頻率）', color=TX, fontsize=14)
ax.set_ylabel('最佳開池 %', color=TX, fontsize=14); ax.tick_params(colors=TX, labelsize=13)
for s in ax.spines.values(): s.set_color('#3a4a40')
ax.grid(color='#24332a'); ax.legend(facecolor=BG, labelcolor=TX, fontsize=12, edgecolor='#3a4a40')
ax.set_title('對手只要防守稍微變寬，SB/BTN 的最佳開池就快速縮回（虛線 = GTO）', color=TX, fontsize=16)
plt.tight_layout(); fig.savefig('rfi_sensitivity.png', dpi=90, facecolor=BG); plt.close(fig)
print('ok')
