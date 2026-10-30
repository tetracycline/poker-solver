# 穩健剝削開池（v8-1031r，已上線 poker-trainer）

來源：`../rfi_audit/`（9 種合理情境逐手重算開池 EV，報告見 `../rfi_audit/REPORT.md`）。

| 位置 | GTO | 純剝削 | **上線（穩健）** | 規則 |
|---|---|---|---|---|
| UTG | 16.3% | 13.4% | **13.1%** | ≥7/9 情境 EV>0 |
| HJ | 21.2% | 18.3% | **15.8%** | ≥7/9 |
| CO | 26.8% | 32.1% | **25.5%** | ≥7/9 |
| BTN | 38.6% | 60.2% | **46.6%** | 9/9 |
| SB | 49.3% | 84.0% | **58.4%** | 9/9 |

範圍：
- UTG：AA–66、AKs–A2s、KQs–KTs、QJs–QTs、JTs、AKo–ATo
- HJ：AA–66、AKs–A2s、KQs–KTs、QJs–QTs、JTs–J9s、T9s、98s、AKo–ATo、KQo–KJo
- CO：AA–44、AKs–A2s、KQs–K5s、QJs–Q8s、JTs–J8s、T9s–T8s、98s–97s、87s–86s、76s、65s、AKo–A8o、KQo–KTo、QJo–QTo
- BTN：所有對子；同花除了 T3s、T2s、94s–92s、84s–82s、73s、72s、63s、62s、52s、42s、32s；A2o+、K7o+、Q9o+、J9o、T9o
- SB：所有對子、所有同花；A2o+、K6o+、Q6o+、J8o+、T8o+、98o、87o

流程（在 box 上）：
1. `make_robust.py`：開池節點鎖成上面的純範圍，其餘位置鎖成 NL2 池，重解 hero 的最佳回應（開池後面對 3-bet／4-bet 的節點因此重新收斂）→ `exploit_robust.json`
2. `ev_robust.py`：每格每動作 EV（同 v8 `ev_compute.py`）→ `ev_robust.json`
3. `build_stage1.py`：同 v8 `build_data.py`（EV 修正、平滑）
4. `patch_rfi.py`：開池節點直接寫入純範圍；EV 欄 = 偏悲觀情境 `shape_adapt25_pen5`（fold EV 不變，open = fold + 該情境差值）；不在自己開池之後的節點保持 v8-1030 原樣（避免重解雜訊）
5. `check_data.py`（單調/頻率檢查 0 違規）、`check_consistency.py`（網頁 21,970 格 vs 評分函式 0 不一致）
