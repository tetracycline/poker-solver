import json, collections, subprocess
C = json.load(open('data/gto_check.json')); S = C['summary']
pc = lambda x: f'{100*x:.1f}%'; pp = lambda x: f'{100*x:+.1f}'
now = subprocess.run(['bash', '-c', 'TZ=Asia/Taipei date "+%Y-%m-%d %H:%M"'], capture_output=True, text=True).stdout.strip()
L = [f'# GTO 理論值 vs 玩家池：剝削規則顯著性檢查（{now} 台北時間）', '',
     '每條剝削規則都對照解算器（/workspace/postflop 的 SRP 4 個開池位置 + 2 個 3bet 底池，共 171 個翻牌、等權）算出 GTO 頻率/組成，再和 NL2 玩家池（SRP 110,876 手、3BP 28,156 手）比較。',
     '', '- 差值 95% CI = 玩家池二項 SE ⊕ GTO 翻牌 bootstrap SE（400 次）',
     '- EV（bb/次）= 偏差可歸因 EV（GTO 無差異點）：棄牌類 |d|·(1+b)·pot；組成類 |d|·(1+2x)·pot',
     '- 判定：**sig** = 方向對、CI 不含 0、EV ≥ 0.05bb；**marg** = CI 不含 0 但 EV < 0.05；**ns** = CI 含 0；**ns_dir** = 顯著但方向和規則假設相反；**gto** = 規則本來就等於 GTO；**nonode** = 解算器沒有這個節點',
     '- ns / ns_dir 的規則在練習裡已改回 GTO 打法（共 31 條：行動線 22、讀牌 9）', '', '## 判定統計', '', '| 分頁 | ' + ' | '.join(['sig', 'marg', 'ns', 'ns_dir', 'gto', 'nonode']) + ' |', '|---|' + '---|' * 6]
for t, n in [('tb', '3-bet'), ('iso', 'Iso'), ('ln', '行動線（196）'), ('rd', '讀牌（組×讀）'), ('all', '合計')]:
    L.append(f'| {n} | ' + ' | '.join(str(S[t].get(k, 0)) for k in ['sig', 'marg', 'ns', 'ns_dir', 'gto', 'nonode']) + ' |')
L += ['', '## 頻率：GTO vs 玩家池', '', '| 項目 | GTO | 玩家池 | 差 (pp) | 95% CI | n | 偏差 EV bb/次* | 顯著 |', '|---|---|---|---|---|---|---|---|']
for k, f in sorted(C['freq'].items(), key=lambda x: -abs(x[1]['d'])):
    L.append(f"| {f['zh']} | {pc(f['gto'])} | {pc(f['pool'])} | {pp(f['d'])} | [{pp(f['lo'])}, {pp(f['hi'])}] | {f['n']:,} | {f.get('ev_dev', 0):.3f} | {'✓' if f['ci_sig'] else '—'} |")
L += ['', '\* 棄牌類 = 對應剝削每次可多賺的 bb；下注頻率類只代表偏差規模（非直接可得 EV）', '', '## 讀牌：對手範圍組成 GTO vs 玩家池', '', '| 讀牌 | 指標 | GTO | 玩家池 | 判定 |', '|---|---|---|---|---|']
for k, r in C['reads'].items():
    if r['verdict'] == 'nonode': L.append(f"| {k} | — | — | — | nonode：{r['note']} |")
    else: L.append(f"| {k} | {r['stat']} | {pc(r['gto'])} | {pc(r['pool'])} | {r['verdict']} |")
L += ['', '## 3-bet：開池者被 3-bet 棄牌', '', '| 開池>你 | GTO 棄 | 玩家池棄 | 差 | 95% CI | GTO 4bet | 池 4bet | EV/詐唬 | 判定 |', '|---|---|---|---|---|---|---|---|---|']
for e in C['rules']:
    if e['tab'] == 'tb': L.append(f"| {e['id']} | {pc(e['gto_f3'])} | {pc(e['pool_f3'])} | {pp(e['d'])} | [{pp(e['lo'])}, {pp(e['hi'])}] | {pc(e['gto_4b'])} | {pc(e['pool_4b'])} | {e['ev_per_bluff']:.2f} | {e['v']} |")
L += ['', '## 行動線：不顯著、已改回 GTO 的規則', '', '| 規則 | 原剝削 | GTO | 依據 | 判定 |', '|---|---|---|---|---|']
for e in C['rules']:
    if e['tab'] == 'ln' and e['v'] in ('ns', 'ns_dir'):
        L.append(f"| {e['id']} | {e['ans']} | {e['gto']} | {e.get('claim_zh','')} GTO {pc(e['gto_ref']) if e.get('gto_ref') is not None else '—'} / 池 {pc(e['pool']) if e.get('pool') is not None else '—'} | {e['v']} |")
L += ['', '## 讀牌：不顯著、已改回 GTO 的組', '', '| 讀牌 | 組 | 原答案 | GTO 答案（GTO 繼續率） | 判定 |', '|---|---|---|---|---|']
for e in C['rules']:
    if e['tab'] == 'rd' and e['v'] in ('ns', 'ns_dir'): L.append(f"| {e['read']} | {e['grp']} | {e['act']} | {e['gto_act']}（{pc(e['gto_p'])}） | {e['v']} |")
L += ['', '## 檔案', '', '- `gto_post.py`：解算器輸出 → `data/gto_flops.pkl`（12.7MB，未上傳，可重建）', '- `pool_post.py`：玩家池計數 → `data/pool_counts.json`', '- `compare.py`：主張/讀牌/規則判定 → `data/gto_check.json`', '- `apply_gto.py`：把判定寫進練習資料（每條加「GTO 約 x%，玩家池 y%」、不顯著改回 GTO）', '- 持續挖掘：`../exploit_mining/`（每 15 分鐘一個假設）']
open('REPORT.md', 'w').write('\n'.join(L) + '\n'); print(len(L))
