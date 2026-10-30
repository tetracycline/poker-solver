# poker-solver

6 人桌 NL 100bb（Natural8 NL2，含 5% 抽水、上限 10bb）的**翻前解算器**、**河牌解算器**和**剝削層**。
這是 [poker-trainer](https://tetracycline.github.io/poker-trainer/) 網站（v8）背後的計算程式和資料。
翻後（翻牌／轉牌／河牌）解算器和練習頁資料在 [`postflop/`](postflop/)，說明見下方「翻後」一節。

- 翻前：向量化 DCFR，169 手牌類別，65 個節點，6000 次迭代後 NashConv 約 0.08 mbb/手。
- 河牌：單條街 CFR+/DCFR，考慮卡牌移除。
- 剝削層：用 NL2 池子 2,334,487 手的**彙總頻率**做節點鎖定，再解出最佳回應。
- 詳細方法和驗證結果請看 [REPORT.md](REPORT.md)。

## 需求

- Python 3.11 以上，加上 `numpy` 和 `matplotlib`（後者只有畫圖才需要）
- Node.js 18 以上
- gcc（只有重新產生勝率矩陣才需要）

```bash
pip install numpy matplotlib
```

## 怎麼跑

以下指令都在 repo 根目錄執行。

```bash
# 1. 直接看練習頁：用瀏覽器打開 solver_drill.html（會讀 data/bundle.js）

# 2. 牌力評估器自我測試，以及重新產生 169×169 勝率矩陣（eq169.bin，已附在 repo 裡）
cd engine && gcc -O2 -o evaltest evaltest.c && ./evaltest
gcc -O2 -o eqmat eqmat.c -lm && ./eqmat 20000 && cd ..

# 3. 翻前 GTO（含抽水／不含抽水）
cd preflop
python3 pfsolve.py --iters 6000 --out gto_rake.json
python3 pfsolve.py --iters 6000 --norake --out gto_norake.json
# 4. 剝削層（讀 inputs/pool_stats.json，輸出 exploit_rake.json）
python3 exploit.py 400
# 5. 檢查單調性、畫範圍圖（輸出到 report_img/）
python3 analyze.py gto_rake.json
python3 charts.py
cd ..

# 6. 河牌：驗證和預算 44 個牌局點（輸出到 data/spots/）
cd river && node test_toy.js && node test_terminal.js && node precompute.js && cd ..
# 只算單一牌局點：node river/precompute.js BTN_BB_bb_b1

# 7. 把翻前＋河牌結果打包成練習頁用的 data/bundle.js
node build_bundle.js

# 8. v8 網站資料：每手每個動作的 EV、平滑後的 pf_data.js，再做一致性檢查
python3 v8_build/build/ev_compute.py      # 約需數分鐘，輸出 v8_build/build/ev.json
python3 v8_build/build/build_data.py      # 輸出 v8_build/out/pf_data.js
python3 v8_build/check/check_data.py
python3 v8_build/check/check_consistency.py   # 和 chart_dump.json（瀏覽器實際畫出的格子）比對
```

`rake_est.py` 是從原始牌譜估計實際抽水的腳本，原始牌譜沒有放進 repo，結果已存在 `data/rake_empirical*.json`。

## 資料夾

```
engine/        C 牌力評估器、169×169 勝率矩陣（eq169.bin）與相容矩陣（compat169.bin）
preflop/       翻前解算器 pfsolve.py、剝削層 exploit.py、分析與畫圖；gto_*.json、exploit_rake.json 是解出來的結果
river/         河牌解算器 river.js、範圍 ranges.js、預算與測試
data/          bundle.js（練習頁資料）、spots/（44 個河牌點）、驗證和抽水估計結果
inputs/        NL2/NL5 池子的彙總統計（pool_stats.json、river_bluff.json），沒有任何原始牌譜
report_img/    REPORT.md 用的圖
v8_build/      產生 v8 網站翻前資料（pf_data.js）的腳本和檢查程式
postflop/      翻後解算流程（driver、Python 管線、檢查、報告），見下方「翻後」
solver_drill.html  解算器練習頁（翻前＋河牌，GTO／剝削切換）
REPORT.md      方法與驗證報告
```

## 沒有放進來的東西

- 原始牌譜（HHDealer 原始檔、data.zip 約 733 MB）和個人 PokerCraft 匯出：只放彙總統計。
- 編譯出來的執行檔、`__pycache__`。
- 網站本身（HTML/CSS/PWA）在 poker-trainer repo。
- 翻後：b-inary/postflop-solver 原始碼（AGPL-3.0，請自行 clone）、`postflop/out/` 原始解（約 1.9 GB）、未壓縮網站資料（124 MB）、編譯產物 `target/`、暫存檔與執行 log。

## 翻後（postflop/）

6 人桌 100bb、5% 抽水上限 10bb，起手範圍直接用 v8 翻前資料（`v8_build/build/pf_data.json`、`preflop/exploit_rake.json`），和翻前解算器一致。
網站：<https://tetracycline.github.io/poker-trainer/postflop/>（剝削 NL2 池為預設，可切 GTO）。方法與驗證結果見 [postflop/report/REPORT_postflop.md](postflop/report/REPORT_postflop.md)。

- 7 個牌局點、90 個翻牌：BTN/CO/SB/UTG/HJ 對 BB 單次加注底池，SB/BB 3-bet 對 BTN。
- 翻牌樹 33%/75% 下注；轉牌子遊戲 50%/100%；河牌 50%/100%/全下。DCFR，翻牌可剝削度中位數 0.46% 底池、轉牌 0.29%。
- 剝削版：把對手鎖成 NL2 池子實際頻率（只用樣本 n ≥ 500 的節點，來源 `inputs/pool_stats.json`），再解我方最佳回應。
- 出題規則：該手牌到達權重 w ≥ 10、節點到達機率 ≥ 0.2%、沒有被標成未收斂或不同尺寸間矛盾；主要動作或頻率 ≥ 25% 的動作都算對。

### 外部解算器（不在 repo 裡）

用的是 [b-inary/postflop-solver](https://github.com/b-inary/postflop-solver)（Rust，AGPL-3.0-or-later），commit `9d1509fe5077d019825f833eed04b16d342dfda1`（2023-10-01）。授權是 AGPL，所以只附上我們自己的 driver，原始碼請自己抓：

```bash
cd postflop
git clone https://github.com/b-inary/postflop-solver.git
git -C postflop-solver checkout 9d1509fe5077d019825f833eed04b16d342dfda1
cd pfdriver && cargo build --release && cd ..   # Rust 1.85 以上（edition 2024）；輸出 pfdriver/target/release/pfdriver
```

`pfdriver/Cargo.toml` 用 `path = "../postflop-solver"` 引用它，所以一定要 clone 到 `postflop/postflop-solver/`。

### 怎麼跑

需求：上面的 Rust 工具鏈、Python 3.11 + numpy + matplotlib、Node.js 18 + `npm install playwright-core` 和 Chrome（只有 UI 檢查需要；Chrome 路徑可用環境變數 `CHROME` 指定）。以下在 `postflop/` 底下執行，路徑都是相對 repo 的。

```bash
# 1. 解算（很花時間，8 核心要好幾個小時以上；需要約 16 GB 記憶體，同時跑太多會被 OOM 砍掉）
python3 py/pipeline.py                      # 全部 7 個牌局點；或 python3 py/pipeline.py BTN_BB 5 只算前 5 個翻牌
python3 py/norake.py BTN_BB,CO_BB,UTG_BB    # 不含抽水的對照（只用於報告 3.4 節）
# 輸出在 out/（不放進 repo）

# 2. 後處理、驗證、報告、檢查（先在另一個終端機跑：python3 -m http.server 18931 --directory site）
bash finish.sh
#    build_site.py → site/postflop/data/；validate.py、consistency.py → report/*.json；
#    make_report.py + assemble_report.py → report/REPORT_postflop.md 與圖；
#    check/check_data.py（資料檢查＋400 題參考答案 grading_ref.json）、check/check_ui.js（網頁判分和參考答案比對）、
#    check/test_pages.js（手機／桌機每個練習項目作答、截圖到 screens/）

# 3. 縮小成網站用資料（124 MB → 約 21.6 MB）
python3 pages/shrink.py          # 去掉到達機率 < 0.2% 的節點（本來就不出題），每個翻牌 gzip 成 .json.gz → pages/postflop/
python3 pages/verify_shrink.py   # 確認所有會出題的節點與可出題手牌數（2,823,186）和縮小前完全一樣
# 把 pages/postflop/ 複製到 poker-trainer repo 的 /postflop/ 就是網站版本；
# 瀏覽器用 DecompressionStream 解壓，舊瀏覽器自動改用 fflate（MIT，site/postflop/fflate.min.js）
```

### 資料夾

```
postflop/
  pfdriver/      Rust driver：讀 job JSON、建樹、解算、鎖定對手頻率、匯出策略/EV/勝率
  py/            管線：ranges.py（起手範圍）、locks.py（NL2 池鎖定）、flops.py（翻牌抽樣）、job.py、pipeline.py、norake.py、
                 build_site.py、validate.py、consistency.py、make_report.py、assemble_report.py、classify.py；bench*.py、memtest.py 是測速／記憶體測試
  check/         check_data.py、check_ui.js、test_pages.js、grading_ref.json（400 題參考答案）
  pages/         shrink.py、verify_shrink.py
  site/postflop/ 練習頁原始碼（index.html、app.js、fflate.min.js）；data/ 由 build_site.py 產生，不放進 repo
  report/        REPORT_postflop.md、圖、validation/consistency/tables/size_conflicts JSON
  finish.sh      後處理一鍵跑完
```

