# poker-solver

6 人桌 NL 100bb（Natural8 NL2，含 5% 抽水、上限 10bb）的**翻前解算器**、**河牌解算器**和**剝削層**。
這是 [poker-trainer](https://tetracycline.github.io/poker-trainer/) 網站（v8）背後的計算程式和資料。
翻後（flop/turn）解算器還在開發，之後會再加進來。

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
solver_drill.html  解算器練習頁（翻前＋河牌，GTO／剝削切換）
REPORT.md      方法與驗證報告
```

## 沒有放進來的東西

- 原始牌譜（HHDealer 原始檔、data.zip 約 733 MB）和個人 PokerCraft 匯出：只放彙總統計。
- 編譯出來的執行檔、`__pycache__`。
- 網站本身（HTML/CSS/PWA）在 poker-trainer repo。
