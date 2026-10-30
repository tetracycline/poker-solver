# 解算器驗證報告 — 6-max NL 100bb（Natural8 NL2）

狀態：解算器、資料和練習頁都已完成並通過驗證。**沒有整合進訓練器，也沒有部署**，等 HW 審閱。
所有檔案都在 `/workspace/outputs/poker_solver/`。

## 0. 一頁摘要

- **翻前**：6 人桌 DCFR，169 手牌類別，65 個節點，含抽水（5%，上限 10bb，無翻牌不抽）。
  - 6000 次迭代後 NashConv **0.08 mbb/手**（無抽水 0.04）。
  - 抽水版 RFI：UTG 16.3%、HJ 21.2%、CO 26.8%、BTN 38.6%、SB 49.3%。
  - 無抽水版 RFI：UTG 21.9%、BTN 47.5%。
  - BB vs BTN 防守：含抽水 45.3%，無抽水 55.7%。
- **河牌**：單條街 CFR+/DCFR，考慮卡牌移除。
  - 玩具遊戲的 bluff 比例和 MDF 與理論誤差 ≤ 0.0002。
  - 44 個真實牌局點的可剝削度最高 **0.10% 底池**（目標是 < 0.5%）。
- **大數據**：用 NL2 池 2,334,487 手的頻率做節點鎖定，再重解出最佳回應。GTO 版和剝削版並列。
  - 翻前每個座位增益 +1.6 到 +5.4 bb/100。
  - 河牌每個牌局點增益中位數約 1bb。
- **練習頁** `solver_drill.html`：翻前和河牌題目，GTO / 剝削切換，13×13 範圍圖，錯題間隔重複，還有「自己解河牌」工具。
  - 在 390×844 和 1280×900 兩種畫面跑無頭測試，**0 個主控台錯誤**。

## 1. 引擎設計

### 1.1 翻前 `preflop/pfsolve.py`

- **算法**：向量化 DCFR（α=1.5，β=0，γ=2），6 個玩家同時更新，169 類別。
  - 卡牌移除用聯合相容矩陣 `engine/compat169.bin` 處理。
  - 169×169 勝率矩陣 `engine/eq169.bin` 由 C 版窮舉評估器 `engine/eqmat.c` 算出。
  - 7 張牌類別頻率與理論值一致（見 `data/validation_terminal.txt`）。
- **尺寸**：
  - 開池 2.5bb，SB 開池 3bb。
  - 3-bet：位置佔優約 3 倍，位置不利約 3.5–4 倍。
  - 4-bet 約 2.2 倍；5-bet 直接全下。
- **完整樹**：RFI → 面對開池（棄牌/跟注/3-bet）→ 面對 3-bet（棄牌/跟注/4-bet）→ 面對 4-bet（棄牌/跟注/全下）→ 面對全下（棄牌/跟注）。
- **單挑抽象**：第一個跟注或 3-bet 的人之後，底池變成單挑。
  - 沒有擠壓（squeeze）、超額跟注（overcall），也沒有 SB 溜入（limp）。
- **翻後價值用「勝率實現」模型**（有文件、參數可調）：
  - 實現勝率用賠率形式：`eq' = eq^a / (eq^a + (1-eq)^a)`。
  - 位置不利的基礎實現率：SRP 0.80、3BP 0.88；位置佔優加成 0.25、位置不利懲罰 0.5，指數 1.5。
  - 可玩性用 PLAY^1.6 修正（同花/連張實現較好，不同花的雜牌較差）。
  - **4-bet 底池**：70% 的翻牌視為全下、按原始勝率結算（扣全下抽水）；其餘 30% 用實現模型。
    - 改成這樣之前，KK 會在面對 5-bet 全下時棄牌（4-bet 平跟讓 67bb 一直沒有進入底池），屬於模型假象。現在已修正。
- **抽水**：
  - 單挑 SRP/3BP 的抽水，按實際 HU 抽水對翻前底池的比例表計算（`data/rake_empirical_hu.json`）。
  - 全下抽水 = min(5%·底池, 10bb) + 1bb jackpot。
  - 無翻牌不抽水。
- **收斂**：NashConv：1000 次迭代 2.30 → 3000 次 0.24 → 6000 次 0.08 mbb/手（`preflop/run_rake.log`）。

### 1.2 河牌 `river/river.js`（瀏覽器與 Node 共用）

- DCFR，攤牌用 O(N) 排序掃描並考慮卡牌移除。
  - 快速終端值與逐對暴力計算的最大誤差為 **4.55e-12**。
- **下注選單**：33% / 75% / 150% / 全下，加注 100%，最多加注 1 次；剩餘籌碼不足 67% 時直接全下。
- **可剝削度** = (BR₀ + BR₁ − 底池) / 2，以底池百分比表示。
- 支援節點鎖定（`lockNode`）和逐手牌的動作 EV（`nodeEVs`）。

## 2. 驗證

### 2.1 河牌玩具遊戲（極化 vs 抓詐，理論 bluff = s/(1+2s)，MDF = 1/(1+s)）

| 下注 s | bluff 比例 | 理論 | 跟注 | MDF | 可剝削度 | 迭代 |
|---|---|---|---|---|---|---|
| 0.33 | 0.1990 | 0.1988 | 0.7517 | 0.7519 | 0.0070% | 400 |
| 0.5 | 0.2502 | 0.2500 | 0.6664 | 0.6667 | 0.0093% | 1000 |
| 0.75 | 0.2999 | 0.3000 | 0.5713 | 0.5714 | 0.0082% | 1800 |
| 1 | 0.3333 | 0.3333 | 0.5000 | 0.5000 | 0.0000% | 200 |
| 1.5 | 0.3751 | 0.3750 | 0.4001 | 0.4000 | 0.0098% | 2200 |
| 2 | 0.4000 | 0.4000 | 0.3335 | 0.3333 | 0.0094% | 1200 |

### 2.2 河牌真實牌局點

- 共 44 個牌局點，可剝削度全部 ≤ **0.10% 底池**；每點 100–500 次迭代，每點 < 0.35 秒。
- 抽查所有頻率 > 5% 的下注動作，共 155 個：
  - 平均 |bluff − 理論| = 0.050。
  - 平均 |繼續 − MDF| = 0.108。
  - 真實範圍不是純極化，所以出現偏差是正常的；方向都一致。
- 例：BTN_BB_bb_b1，IP 在對手過牌後：

  | 下注 | bluff 比例（理論） | 繼續率（MDF） |
  |---|---|---|
  | 33% | 0.19（0.20） | 0.74（0.75） |
  | 75% | 0.26（0.30） | 0.56（0.57） |

### 2.3 翻前 vs 公開數字

| | 本解（含抽水） | 本解（無抽水） | 公開參考 |
|---|---|---|---|
| UTG RFI | 16.3% | 21.9% | 15–18% |
| HJ RFI | 21.2% | 26.3% | 19–22% |
| CO RFI | 26.8% | 32.0% | 26–30% |
| BTN RFI | 38.6% | 47.5% | 40–48% |
| SB RFI | 49.3% | 49.6% | 40–50%（只用加注的策略） |
| BB vs BTN 防守 | 45.3% | 55.7% | ~60%+（無抽水） |

和公開數字的差異說明：

1. **抽水把範圍收緊**。NL2 抽水很重：每個單挑 SRP 翻牌約 0.65bb，約佔翻前底池 12%。所以含抽水版的範圍明顯比公開的「無抽水」圖表緊，特別是 BTN 開池和 BB 防守。
2. **無抽水版與公開數字吻合**：BTN 47.5%、BB 防守 55.7%。
   - UTG 21.9% 偏寬，因為模型沒有擠壓和多人底池，後面玩家的懲罰較小。
   - BB 防守略低於 60%，因為勝率實現表偏保守。

### 2.4 單調性檢查（`data/monotonic_*.txt`、`data/monotonic_ev_*.txt`）

- 抽水版有 15 個格子違反單調性，無抽水版有 16 個。逐一計算動作 EV 後，**全部都是近乎無差異（≤ 0.25bb）**：
  - **A5s 比 A6s 更常 4-bet 詐唬**：A5s 4-bet −2.27 vs 棄牌 −2.50，A6s 4-bet −2.70。原因是 A5s 的順子潛力較好，而且同樣有 A 阻擋牌。這是標準 GTO 現象。
  - **TT 跟注 4-bet、JJ 卻棄牌**（BB vs CO 的 4-bet）：TT 跟注 −10.01 vs 棄牌 −10.00，JJ 跟注 −10.24。兩者都在無差異邊緣，差距在模型誤差內，不是真正的策略訊號。
  - **A8s/A9s、KTs/KJs**：差距 ≤ 0.05bb，屬於混合策略的隨機落點。

## 3. 大數據剝削層

**資料**：`/workspace/poker/hhdealer/pool_stats.json`（NL2，2,334,487 手）。

**翻前方法**（`preflop/exploit.py`）：

- 有資料的節點，把對手鎖定到池中的頻率：
  - RFI 用 `open_raise`，溜入算作棄牌。
  - 面對開池用 `vs_open`（n ≥ 1000）。
  - 面對 3-bet 用 `f3`；面對 4-bet 用 `fold_to_4bet`。
- 同一個動作裡由哪些手牌執行，按 STR（對隨機手牌的勝率）**線性排序**分配。
- 然後只重解自己的座位（300 次迭代），得到最佳回應。
- 樣本量：每個節點 n = 21,583–1,741,758，95% 信賴區間都在 ±0.7 個百分點以內，統計上很穩。
- **主要誤差來源是模型假設**：線性排序，以及池子的選擇偏差。

| 座位 | EV 剝削（bb/100） | EV GTO 對池（bb/100） | 增益（bb/100） |
|---|---|---|---|
| UTG | +14.1 | +9.1 | +5.0 |
| HJ | +15.2 | +10.2 | +5.0 |
| CO | +16.9 | +12.6 | +4.3 |
| BTN | +21.7 | +16.3 | +5.4 |
| SB | −25.2 | −29.9 | +4.7 |
| BB | −51.4 | −53.0 | +1.6 |

主要的剝削方向（GTO → 剝削）：

- BTN 開池 38.6 → 60.2%，SB 開池 49.3 → 84%，因為池子在盲注位棄牌太多。
- CO 開池、BTN 3-bet：8.4 → 26.3%。
- BTN 面對 BB 3-bet 時棄牌 55.5 → 90%，因為池子的 3-bet 範圍很價值重。
- BB vs UTG 跟注 22.3 → 29.5%。
- BB vs SB 棄牌 41.3 → 49.5%。

**河牌方法**（`river/precompute.js`）：

- 對手面對下注的節點，鎖定到 `river_bluff.json` 的 `by_line_size[線路 | 尺寸區間]`（棄牌/加注）。
  - 362 個鎖定，n = 1,065–19,009（中位數 4,402），95% 信賴區間 ≤ ±3 個百分點。
  - 大於 2 倍底池的下注，池子的棄牌上限設為 GTO 的棄牌率。
- bb 線（翻牌和轉牌都下注）時，對手的河牌下注頻率也鎖定。
  - 用 `river_barrel` 的下注率，空氣佔 20.6%，保留 80% 的慢打（TRAP_KEEP 0.8）。
- 每個牌局點的增益（bb）：

  | 家族 | 中位數 | 範圍 |
  |---|---|---|
  | BTN_BB_bb | 1.1 | 0.3–2.2 |
  | CO_BB_bb | 1.3 | 0.2–2.4 |
  | SB_BB_bb | 1.4 | 1.1–2.0 |
  | BTN_BB_bx | 0.4 | 0–1.6 |
  | BTN_BB_xx | 0.8 | −0.1–2.4 |
  | SB_BB_bx | 0.6 | −0.2–1.7 |
  | BB3_BTN_bx | 1.4 | 0.4–3.0 |
  | BB3_BTN_bb | 3.3 | 2.8–13.5 |

  - 13.5bb 那個是 85bb 底池的 b3 牌面，主要來自線性排序假設，**應視為上限**。
  - 少數增益是負的，因為重解時池子未鎖定的節點也會調整。

### 3.1 HW 自己的數據（938 手，n 很小，附 95% Wilson 信賴區間）

| 統計 | HW | 信賴區間 | GTO（含抽水）參考 |
|---|---|---|---|
| BB 面對偷盲時防守 | 12/61 = 20% | 12–31% | vs BTN 45%，vs SB 59% |
| 翻牌面對 c-bet 棄牌 | 10/17 = 59% | 36–78% | 約 35–45%（MDF） |
| 偷盲 | 52/229 = 23% | 18–29% | CO–SB 約 27–49% |
| SB 面對偷盲棄牌 | 49/58 = 84% | 73–92% | SB vs BTN 70% |
| 3-bet | 14/344 = 4% | 2–7% | — |
| 面對 3-bet 棄牌 | 6/12 = 50% | 25–75% | BTN vs BB 55% |
| VPIP / PFR | 18% / 14% | 15–20 / 11–16 | — |

**結論**：BB 防守過少在統計上很明確（信賴區間上限 31%，仍遠低於 45%）；面對 c-bet 棄牌過多的方向成立，但樣本小。練習頁有 BB 防守和河牌防守兩個專項篩選。

## 4. 圖表（翻前，左 GTO 含抽水、右剝削 NL2 池）

- **顏色**：綠 = 開池，藍 = 跟注，紅 = 3-bet/4-bet，紫 = 全下，深色 = 棄牌。
- 格子內的寬度是動作比例，高度是到達該節點的機率；完全空白代表那手牌不在範圍內。
- 比例按到達機率加權（同一節點的手牌組合）。

| 牌局點 | 節點 | 動作 | GTO % | 剝削 % |
|---|---|---|---|---|
| UTG 開池 | `UTGrfi` | fold/open | 83.7 / 16.3 | 86.6 / 13.4 |
| HJ 開池 | `HJrfi` | fold/open | 78.8 / 21.2 | 81.4 / 18.6 |
| CO 開池 | `COrfi` | fold/open | 73.2 / 26.8 | 67.9 / 32.1 |
| BTN 開池 | `BTNrfi` | fold/open | 61.4 / 38.6 | 39.8 / 60.2 |
| SB 開池（對 BB） | `SBrfi` | fold/open | 50.7 / 49.3 | 16.0 / 84.0 |
| BB vs UTG 開池 | `UTGopen>BB` | fold/call/3bet | 73.0 / 22.3 / 4.7 | 67.9 / 29.5 / 2.6 |
| BB vs HJ 開池 | `HJopen>BB` | fold/call/3bet | 68.9 / 25.4 / 5.7 | 66.7 / 29.9 / 3.5 |
| BB vs CO 開池 | `COopen>BB` | fold/call/3bet | 64.9 / 27.3 / 7.8 | 64.5 / 29.1 / 6.3 |
| BB vs BTN 開池 | `BTNopen>BB` | fold/call/3bet | 54.7 / 34.4 / 10.9 | 56.2 / 33.1 / 10.7 |
| BB vs SB 開池 | `SBopen>BB` | fold/call/3bet | 41.3 / 45.1 / 13.6 | 49.5 / 38.9 / 11.6 |
| SB 開池後 vs BB 3-bet | `SBopen>BB3b` | fold/call/4bet | 50.9 / 37.2 / 11.9 | 88.9 / 6.5 / 4.7 |
| SB vs BTN 開池（3-bet or fold） | `BTNopen>SB` | fold/call/3bet | 70.1 / 19.2 / 10.7 | 70.1 / 10.6 / 19.4 |
| BTN vs CO 開池 | `COopen>BTN` | fold/call/3bet | 76.9 / 14.7 / 8.4 | 68.6 / 5.1 / 26.3 |
| BTN vs UTG 開池 | `UTGopen>BTN` | fold/call/3bet | 86.4 / 8.4 / 5.2 | 83.0 / 11.8 / 5.3 |
| BTN 開池後 vs BB 3-bet | `BTNopen>BB3b` | fold/call/4bet | 55.5 / 33.3 / 11.2 | 90.1 / 5.3 / 4.5 |
| CO 開池後 vs BTN 3-bet | `COopen>BTN3b` | fold/call/4bet | 43.5 / 44.9 / 11.7 | 65.6 / 25.9 / 8.5 |
| UTG 開池後 vs BB 3-bet | `UTGopen>BB3b` | fold/call/4bet | 56.8 / 29.8 / 13.3 | 67.4 / 15.7 / 16.9 |
| BB 3-bet 後 vs BTN 4-bet | `BTNopen>BB3b>4b` | fold/call/jam | 68.6 / 27.5 / 3.9 | 87.3 / 0.0 / 12.7 |
| BTN 3-bet 後 vs CO 4-bet | `COopen>BTN3b>4b` | fold/call/jam | 67.5 / 22.1 / 10.4 | 94.8 / 3.4 / 1.7 |
| BTN 4-bet 後 vs BB 全下 | `BTNopen>BB3b>4b>jam` | fold/call | 36.5 / 63.5 | 66.7 / 33.3 |

**UTG 開池**

![UTGrfi](report_img/pf_UTGrfi.png)

**HJ 開池**

![HJrfi](report_img/pf_HJrfi.png)

**CO 開池**

![COrfi](report_img/pf_COrfi.png)

**BTN 開池**

![BTNrfi](report_img/pf_BTNrfi.png)

**SB 開池（對 BB）**

![SBrfi](report_img/pf_SBrfi.png)

**BB vs UTG 開池**

![UTGopen>BB](report_img/pf_UTGopen_BB.png)

**BB vs HJ 開池**

![HJopen>BB](report_img/pf_HJopen_BB.png)

**BB vs CO 開池**

![COopen>BB](report_img/pf_COopen_BB.png)

**BB vs BTN 開池**

![BTNopen>BB](report_img/pf_BTNopen_BB.png)

**BB vs SB 開池**

![SBopen>BB](report_img/pf_SBopen_BB.png)

**SB 開池後 vs BB 3-bet**

![SBopen>BB3b](report_img/pf_SBopen_BB3b.png)

**SB vs BTN 開池（3-bet or fold）**

![BTNopen>SB](report_img/pf_BTNopen_SB.png)

**BTN vs CO 開池**

![COopen>BTN](report_img/pf_COopen_BTN.png)

**BTN vs UTG 開池**

![UTGopen>BTN](report_img/pf_UTGopen_BTN.png)

**BTN 開池後 vs BB 3-bet**

![BTNopen>BB3b](report_img/pf_BTNopen_BB3b.png)

**CO 開池後 vs BTN 3-bet**

![COopen>BTN3b](report_img/pf_COopen_BTN3b.png)

**UTG 開池後 vs BB 3-bet**

![UTGopen>BB3b](report_img/pf_UTGopen_BB3b.png)

**BB 3-bet 後 vs BTN 4-bet**

![BTNopen>BB3b>4b](report_img/pf_BTNopen_BB3b_4b.png)

**BTN 3-bet 後 vs CO 4-bet**

![COopen>BTN3b>4b](report_img/pf_COopen_BTN3b_4b.png)

**BTN 4-bet 後 vs BB 全下**

![BTNopen>BB3b>4b>jam](report_img/pf_BTNopen_BB3b_4b_jam.png)


## 5. 練習頁 `solver_drill.html`

**結構**：

- 分頁：翻前 `#pre`、河牌 `#riv`、自己解河牌 `#tool`、說明 `#about`。
- GTO / 剝削 NL2 池切換，題目篩選（全部、BB 防守、河牌面對下注）。

**作答與顯示**：

- 熱鍵：R = 加注/下注，C = 跟注/過牌，F = 棄牌，Space/Enter = 下一題。
- 手機上答題按鈕固定在畫面底部（sticky）。
- 揭曉後顯示：混合策略和各動作 EV、另一個版本（GTO 或剝削）的對照、中文解說（底池賠率、MDF、bluff 比例、EV 差、池子鎖定和 n），以及 13×13 範圍圖。
- **錯題間隔重複**（localStorage `solverDrill.v1`）：答錯在 3 題後重出（再錯為 2 題），之後第 9 題再出一次；半對的在 6 題後重出。

**資料**：`data/bundle.js`（4.8MB，離線可用），內含翻前 65 個節點（GTO、無抽水、剝削）和 44 個河牌牌局點。

**測試**：`/workspace/poker_mb/solver/test_drill.js`

- 兩種畫面各答 25 題翻前和 25 題河牌，切換剝削版，執行解算工具（150 次迭代，184ms，可剝削度 0.11%），開啟說明頁。
- **0 個主控台錯誤**；固定按鈕列位置 771–844px（fixed）。
- 截圖在 `/workspace/poker_mb/solver/`。

![翻前作答](report_img/mobile_pre_ans.png) ![河牌作答](report_img/mobile_riv_ans.png) ![河牌防守剝削](report_img/mobile_riv_def_exploit.png)

![自己解河牌](report_img/desktop_tool.png)

## 6. 檔案

| 路徑 | 內容 |
|---|---|
| `preflop/pfsolve.py` | 翻前解算器 |
| `preflop/gto_rake.json`、`preflop/gto_norake.json` | GTO 解 |
| `preflop/exploit.py`、`preflop/exploit_rake.json` | 剝削層 |
| `preflop/analyze.py`、`preflop/mono_ev.py` | 單調性檢查和 EV |
| `preflop/charts.py` → `report_img/pf_*.png` | 範圍圖 |
| `river/river.js` | 河牌引擎 |
| `river/ranges.js` | 範圍工具 |
| `river/precompute.js` → `data/spots/*.json`（44）、`data/spots_index.json`、`data/precompute.log` | 河牌預算 |
| `engine/` | C 評估器和勝率矩陣 |
| `build_bundle.js` → `data/bundle.js` | 練習頁資料包 |
| `solver_drill.html` | 練習頁 |

## 7. 限制

1. **翻後是模型，不是解出來的**：翻前的翻後價值是勝率實現的啟發式表，參數已記錄，可調。
2. **單挑抽象**：沒有擠壓、超額跟注、SB 溜入。UTG 和 HJ 在無抽水時因此偏寬。
3. **剝削層假設池子的手牌按強度線性分配**，但真實池子會混雜（例如慢打 AA、拿雜牌 3-bet）。所以剝削增益是**模型上限**，最佳回應的策略也很極端（例如 SB 開池 84%）。實戰建議只用一半的方向。
4. **池子資料有選擇偏差**：攤牌或被跟注的手牌才看得到。
5. **河牌範圍來自線路過濾的啟發式**（翻牌/轉牌下注或過牌的比例），不是逐街解出來的。河牌不計抽水。
6. **HW 樣本只有 938 手**，除了 BB 防守，其他統計的信賴區間都很寬。

## 8. 整合計畫（尚未執行）

- 在訓練器加一個「解算器」分頁，深連結 `#solver`，用 iframe 或直接載入 `solver_drill.html#pre|riv|tool|about`。
- 資料包可以獨立更新。
- 等 HW 確認以上數字和模型後，再用同一套資料重建訓練器題庫。
- 沒有修改 `/workspace/outputs/poker_pwa/`，也沒有部署。
