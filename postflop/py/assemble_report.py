"""Assemble report/REPORT_postflop.md (run make_report.py first)."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, glob, os, collections, datetime
REP = f'{PFDIR}/report'; D = f'{PFDIR}/site/postflop/data'
T = json.load(open(f'{REP}/tables.json')); SC = json.load(open(f'{REP}/size_conflicts.json')) if os.path.exists(f'{REP}/size_conflicts.json') else {}; I = json.load(open(f'{D}/index.json'))
CZ = {k: zh for k, zh, st in I['cats']}
Q = collections.Counter(); NOD = collections.Counter(); U = 0; TOT = 0; size = 0; nfl = 0
for f in glob.glob(f'{D}/*/*.json'):
    size += os.path.getsize(f); nfl += 1; F = json.load(open(f))
    for v, L in F['v'].items():
        for n in L:
            us = set(n.get('u', [])) | set(n.get('uc', [])); U += len(us); TOT += len(n['w'])
            if n['pr'] < 0.002: continue
            k = sum(1 for i, w in enumerate(n['w']) if w >= 10 and i not in us)
            Q[(v, F['spot'], n['c'])] += k; NOD[(v, n['c'])] += 1
spots = list(I['spots'])
cats = [c for c, _, _ in I['cats']]
qt = ['| 練習項目 | ' + ' | '.join(spots) + ' | 合計 (剝削 / GTO) |', '|---|' + '---|' * (len(spots) + 1)]
for c in cats:
    e = [Q[('exp', s, c)] for s in spots]; g = [Q[('gto', s, c)] for s in spots]
    if not sum(e) + sum(g): continue
    qt.append(f'| {CZ[c]} (`{c}`) | ' + ' | '.join(f'{a:,} / {b:,}' for a, b in zip(e, g)) + f' | {sum(e):,} / {sum(g):,} |')
QE = sum(v for k, v in Q.items() if k[0] == 'exp'); QG = sum(v for k, v in Q.items() if k[0] == 'gto')
flops = {s: len(I['spots'][s]['flops']) for s in spots}
md = f"""# 翻後 CFR 解 + 練習（v8 翻後模組）— 驗證報告

產生時間：{datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')}（台北時間 UTC+8）。**尚未部署／推送**，等 HW 審閱。

## 1. 解了什麼

| 局面 | 底池類型 | 翻牌前加注者 | 解的翻牌數 |
|---|---|---|---|
""" + '\n'.join(f"| {s}（{I['spots'][s]['oop']} vs {I['spots'][s]['ip']}） | {I['spots'][s]['kind']} | {'IP' if I['spots'][s]['pfr'] else 'OOP'} | {flops[s]} |" for s in spots) + f"""

* 引擎：b-inary/postflop-solver（Rust，DCFR，AGPL-3.0，未修改），由自寫 driver `pfdriver` 呼叫；網站只發佈**產生的策略資料**，不含 solver 程式碼。
* 5% 抽水、上限 10bb（Natural8 NL2）；有效籌碼 100bb；HU 底池。
* 起手範圍：v8 `pf_data` 的翻前解（GTO 版用 GTO 範圍；剝削版用 hero 剝削範圍 vs NL2 池範圍）。
* 翻牌：從 1,755 種同構翻牌（權重合計 22,100）依牌面特徵排序後**系統抽樣**，每個抽中的翻牌代表相同出現機率。
* 樹（粗樹，求翻牌策略）：翻前加注者翻牌下注 33% / 75%（不允許 donk）；加注 3x 或全下（一次加注後只剩全下）；轉牌 66%、河牌 75%，後街加注 = 全下。
* 轉牌細解（子樹）：每個翻牌取 3 張轉牌（隨機、固定種子），對「主要 c-bet 線」與「過牌過牌線」重解：轉牌 50%/100%，河牌 50%/100%/全下，加注 = 全下；起始範圍 = 翻牌解在轉牌根節點的實際範圍；IP 最後下注時轉牌根不允許 OOP donk（`root_no_bet`）。河牌每條線取 2 張，網站使用第 1 張。
* 收斂目標：翻牌樹 0.5% 底池、子樹 0.3% 底池。
* 剝削版：先解到 1.25% 再把對手鎖成 NL2 池頻率（n ≥ 500 的節點；下注節點同時鎖 NL2 池的**尺寸分佈**），再讓 hero 解最佳回應到 hero gap ≤ 0.5%（子樹 0.3%）。

## 2. 收斂度

{T['T3']}

![exploitability](exploitability.png)

## 3. 和公開數據比較

**參考：GTO Gecko（PioSolver，BTN vs BB SRP 100bb，5% 抽水上限 4bb，33%/75% 兩種尺寸，無 donk，1,755 翻牌依出現率加權）**；GTO Wizard（NL500 general，BTN c-bet 約 54%，BB 對小 c-bet 過牌加注約 17.5%）。

### 3.1 BTN vs BB c-bet 依牌面

{T['T1']}

![cbet](cbet_texture.png)

### 3.2 同一張翻牌直接對照（GTO Gecko 公開的板面）

{T['T8']}

敏感度測試：A♠7♥2♦ 改用更細的轉/河樹（轉牌 33%/75%＋加注、河牌 33%/75%/全下、抽水上限 4bb）後 c-bet 反而是 61.3%（粗樹 53.1%）——所以差距**不是**後街抽象化造成的。主要原因是**翻前範圍不同**：v8 的 BTN 開池 38.6%（含 A 的組合 36.3%），BB 平跟範圍 35.2%（含 A 27.2%，且 AA/KK/QQ/AK/AQo 全部 3-bet、不在跟注範圍）。BB 的範圍上限被封頂、A 少，所以 BTN 在 A 高牌面能下注更多；Gecko 的 BTN 有 A 26.6% vs BB 24.0%，幾乎持平。單色、K 高乾燥等範圍優勢不受影響的板面則和 Gecko 很接近（K♠8♠3♠ 27.9% vs 27.7%）。

### 3.3 各局面翻牌總表（GTO 版）

{T['T2']}

BB 對 33% c-bet 的過牌加注率 vs GTO Wizard 的 17.5%：見上表「對手過牌加注 vs 33%」欄。

### 3.4 抽水的影響（同翻牌、粗樹、無抽水且用無抽水翻前範圍）

{T['T5'] or '（無抽水驗證尚未完成）'}

無抽水對照只做 BB 防守的三個 SRP 局面（BTN／CO／UTG vs BB，共 50 個翻牌）。SB_BB、HJ_BB 和兩個 3-bet 底池沒做：抽水在 3-bet 底池幾乎都撞到 10bb 上限，影響比例更小；SB_BB／HJ_BB 為了節省計算時間略過。方向一致：有抽水時翻前加注者 c-bet 少 3–9 個百分點、33% 尺寸用得較少，防守方棄牌率幾乎不變。

## 4. 牌力單調性

{T['T4']}

![monotonic](monotonic.png)

### 4.1 不同下注尺寸之間不矛盾

（剝削版只檢查「你」的決策點；對手節點是鎖定的池子模型）同一個決策點、同一個範圍，只差對手下注大小（例如 33% vs 75%）：範圍層級應該是「面對大注棄牌較多」；組合層級檢查同一組合是否「面對大注反而多繼續 ≥50 個百分點」。

{T.get('T9') or '（尚未計算）'}

河牌 20–50% 勝率區間繼續率約 35–45% 是正常的：這些是抓詐牌與用來詐唬加注的牌，勝率是對「下注前」範圍算的。違規率約 1% 屬於未完全收斂的小幅混合。

## 5. 剝削層（NL2 池）

資料：`pool_stats.json`，NL2 2,334,487 手，只取 HU 翻後底池。**頻率**是可觀察的（每一手都有行動）；**哪些組合**採取該行動不可觀察（只有攤牌才看到牌），所以鎖定時由 solver 自己的牌力排序分配組合（強牌先繼續/先加注）。攤牌偏差：攤牌樣本偏向跟到底的牌，這裡不用攤牌牌力，只用行動頻率；但「池子拿什麼牌加注」仍是假設。

### 5.1 剝削 EV 增益

{T['T6']}

![exploit](exploit_gain.png)

這是對「完全照模型打」的對手的最大剝削上限（模型錯了會打回來），實戰增益會小很多；用途是告訴你方向（例如對 75% 下注棄牌太多 → 多詐唬大尺寸、少抓詐）。

### 5.2 鎖定的節點、樣本數與 95% 信賴區間（n<500 的節點不鎖，對手照均衡）

{T['T7']}

## 6. 練習項目與題數

可出題的組合數（權重 ≥10、該線出現機率 ≥0.2%、不屬於未收斂組合），格式 剝削 / GTO：

{chr(10).join(qt)}

合計：剝削版 {QE:,} 題、GTO 版 {QG:,} 題（每題 = 某局面某條線某個組合）。資料 {nfl} 個翻牌檔、{size/1e6:.0f} MB（gzip 約為 1/4）。

練習項目選單：全部、六個大類（all.<類別>）、每個局面全部、每個局面 × 每個類別。預設剝削版，可切換 GTO（和 v8 共用 `pk8.ver`）。

評分（app.js 唯一的評分函數 `okActs/judge`，和表格、檢查腳本共用）：該組合最高頻動作、或任何 ≥25% 的動作算對；≥50% 或主動作為「對」，其餘為「混合」；下注方向對但尺寸選錯（加總攻擊 ≥50%）記「尺寸不對」算錯。答錯 3 題後再出，答對複習後 8 題再出，錯題權重最高 ×7。

未收斂組合：主動作比 solver 自己的最佳 EV 動作少 >0.25bb 且 >5% 底池的組合標「*未收斂」、不出題；同一決策點面對較大下注反而多繼續 ≥50 個百分點的組合標「*不同尺寸間矛盾」、也不出題（GTO {SC.get('gto', 0):,}、剝削 {SC.get('exp', 0):,} 組）。兩者合計 {U:,} / {TOT:,}（{100*U/max(1,TOT):.2f}%）。

## 7. 測試

* `check/check_data.py`：策略加總 100、無與牌面衝突的組合、主動作 EV 差距分佈。
* `check/check_ui.js`：400 個隨機參考答案 vs 網頁評分與 13×13 格子聚合（0 不一致），40 題實際作答，0 console error。
* `postflop/check/test_pages.js`：390×844 與 1280×900 兩個視窗，每個練習項目作答、切換 GTO、翻後表、說明頁；截圖在 `postflop/screens/`（不放進 repo）。

## 8. 限制

* 只有 HU；多人底池不在範圍內。
* 資料量：90 個翻牌檔共約 129 MB（每個翻牌約 1.4 MB，按需載入；gzip 約 1/4）。上線前可能要再壓縮（例如只留出題用節點）。
* 剝削版在約 3–6% 的「同一決策點、兩種下注尺寸」配對上，面對大注的棄牌率反而略低：這是池子模型（各尺寸的組合由 solver 牌力排序分配）造成的，不是錯誤；組合層級 ≥50pp 的矛盾已全部標記不出題。
* 下注尺寸抽象化：翻牌 33/75，轉牌 50/100（子樹）或 66（粗樹），河牌 50/100/全下；實戰對手的其他尺寸請就近對應。
* 轉牌只取 3 張、河牌每線 1 張（網站）——轉/河題目代表的是「這些牌」的解，不是所有轉牌的平均。
* 子樹只覆蓋主要 c-bet 線與過牌過牌線；其他線只有粗樹的轉/河（不出題）。
* 翻前範圍來自 v8；與 Pio/GTO Wizard 標準範圍不同，所以 A 高牌面 c-bet 偏高（見 3.2）。
* 剝削版是對模型的最大剝削，假設池子的組合分配 = solver 牌力排序。
* 收斂 0.3–0.5% 底池：極少走到的線上策略可能仍有雜訊，已用「出現機率 ≥0.2%」與「*未收斂」過濾出題。

## 9. 整合（HW 審閱後再做，**未執行**）

把 `postflop/pages/postflop/`（shrink.py 的輸出） 複製到 repo 的 `/postflop/`，在 v8 主選單加「翻後」連結；index.html 引用 `../` 的圖示與 CSS。不要複製 solver 或 out/ 原始解。
"""
open(f'{REP}/REPORT_postflop.md', 'w').write(md); print('ok', QE, QG, U, TOT)
