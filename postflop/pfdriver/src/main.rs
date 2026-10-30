// Driver around b-inary/postflop-solver (AGPL-3.0, used unmodified as a local library; only generated data is published).
use postflop_solver::*;
use serde::Deserialize;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::Instant;

#[derive(Deserialize, Clone)]
struct Lock { pat: String, #[serde(default)] fold: Option<f32>, #[serde(default)] raise: Option<f32>, #[serde(default)] bet: Option<f32>, #[serde(default)] sizes: Option<Vec<(f32, f32)>> }
#[derive(Deserialize)]
struct Extract { prefix: Vec<String>, #[serde(default)] street: bool, #[serde(default)] raw: bool }
#[derive(Deserialize)]
struct Job {
    flop: String, pot: i32, stack: i32, rake_rate: f64, rake_cap: f64,
    #[serde(default)] root_no_bet: bool,
    #[serde(default)] oop: String, #[serde(default)] ip: String,
    #[serde(default)] oop_w: Vec<(String, f32)>, #[serde(default)] ip_w: Vec<(String, f32)>,
    #[serde(default)] turn: Option<String>,
    #[serde(default)] line0: Vec<String>,
    flop_oop: String, flop_ip: String, flop_raise: String,
    turn_oop: String, turn_ip: String, turn_raise: String,
    river_oop: String, river_ip: String, river_raise: String,
    #[serde(default)] turn_donk: Option<String>, #[serde(default)] river_donk: Option<String>,
    iters: u32, target_pct: f32,
    #[serde(default)] hero: Option<usize>,
    #[serde(default)] rank_pct: Option<f32>,
    #[serde(default)] locks: Vec<Lock>,
    #[serde(default)] extract: Vec<Extract>,
    out: String,
    #[serde(default)] compress: bool,
}

fn label(a: &Action, pot_before: i32, prev_bet: i32) -> String {
    match a {
        Action::Fold => "f".into(), Action::Check => "x".into(), Action::Call => "c".into(),
        Action::Bet(x) => format!("b{}", ((*x as f64) * 100.0 / pot_before as f64).round() as i32),
        Action::Raise(_) => { let _ = prev_bet; "r".into() },
        Action::AllIn(_) => "a".into(),
        _ => "?".into(),
    }
}

// cap raises: at most one sized raise per street; afterwards only all-in
fn prune(tree: &mut ActionTree, raises: u32) {
    if tree.is_terminal_node() { return; }
    let acts: Vec<Action> = tree.available_actions().to_vec();
    if raises >= 1 {
        for a in &acts { if let Action::Raise(_) = a { let _ = tree.remove_action(*a); } }
    }
    let acts: Vec<Action> = tree.available_actions().to_vec();
    for a in acts {
        tree.play(a).unwrap();
        if tree.is_terminal_node() { tree.undo().unwrap(); continue; }
        let nr = if tree.is_chance_node() { 0 } else { match a { Action::Raise(_) | Action::AllIn(_) => raises + 1, _ => raises } };
        prune(tree, nr);
        tree.undo().unwrap();
    }
}

struct Ctx { line: Vec<String>, }

fn node_pot(g: &PostFlopGame) -> (i32, [i32; 2]) { let b = g.total_bet_amount(); (g.tree_config().starting_pot + b[0] + b[1], b) }

fn act_labels(g: &PostFlopGame) -> Vec<String> {
    let (_pot, b) = node_pot(g);
    let mn = b[0].min(b[1]); let mx = b[0].max(b[1]);
    let base = g.tree_config().starting_pot + 2 * mn; // pot before the current bet
    g.available_actions().iter().map(|a| label(a, base, mx - mn)).collect()
}

fn line_str(c: &Ctx) -> String { c.line.join(" ").replace(" / ", "/").replace(" /", "/").replace("/ ", "/") }

fn card_str(c: u8) -> String { card_to_string(c).unwrap() }

// apply pool-frequency lock to current node given villain reach r
fn make_lock(g: &PostFlopGame, lk: &Lock, reach: &[f32]) -> Vec<f32> {
    let s = g.strategy(); let acts = g.available_actions(); let na = acts.len(); let nh = reach.len();
    let tot: f64 = reach.iter().map(|&x| x as f64).sum();
    let mut out = vec![0f32; na * nh];
    if tot <= 0.0 { return s; }
    let ifold = acts.iter().position(|a| *a == Action::Fold);
    let iraise: Vec<usize> = acts.iter().enumerate().filter(|(_, a)| matches!(a, Action::Raise(_) | Action::AllIn(_) | Action::Bet(_))).map(|(i, _)| i).collect();
    let ipass = acts.iter().position(|a| *a == Action::Call || *a == Action::Check).unwrap();
    // aggressive mass per hand
    let agg = |h: usize| -> f32 { iraise.iter().map(|&i| s[i * nh + h]).sum() };
    let mix_avg: Vec<f64> = { let mut m = vec![0f64; iraise.len()]; for h in 0..nh { for (k, &i) in iraise.iter().enumerate() { m[k] += (reach[h] * s[i * nh + h]) as f64; } } let t: f64 = m.iter().sum(); if t > 0.0 { m.iter().map(|x| x / t).collect() } else { let mut v = vec![0.0; iraise.len()]; if !v.is_empty() { v[0] = 1.0; } v } };
    // fill helper: given score per hand (higher = more likely to take 'X'), target mass fraction, return per-hand prob of X among weight w
    fn fill(score: &[f32], w: &[f64], target: f64) -> Vec<f64> {
        let nh = score.len(); let tot: f64 = w.iter().sum(); let mut p = vec![0f64; nh];
        if tot <= 0.0 { return p; }
        let mut idx: Vec<usize> = (0..nh).collect(); idx.sort_by(|&a, &b| score[b].partial_cmp(&score[a]).unwrap());
        let mut need = (target.clamp(0.0, 1.0)) * tot; let mut i = 0;
        while i < nh && need > 1e-12 {
            // tie group
            let mut j = i; let mut gw = 0.0; while j < nh && (score[idx[j]] - score[idx[i]]).abs() < 1e-4 { gw += w[idx[j]]; j += 1; }
            let f = if gw <= need { 1.0 } else { need / gw };
            for k in i..j { p[idx[k]] = f; }
            need -= gw * f; i = j;
        }
        p
    }
    let w: Vec<f64> = reach.iter().map(|&x| x as f64).collect();
    if let (Some(fi), Some(ft)) = (ifold, lk.fold) {
        let cont: Vec<f32> = (0..nh).map(|h| 1.0 - s[fi * nh + h]).collect();
        let pc = fill(&cont, &w, 1.0 - ft as f64); // continue prob
        let rt = lk.raise.unwrap_or_else(|| { let m: f64 = (0..nh).map(|h| w[h] * agg(h) as f64).sum(); (m / tot) as f32 }) as f64;
        let wc: Vec<f64> = (0..nh).map(|h| w[h] * pc[h]).collect();
        let ag: Vec<f32> = (0..nh).map(|h| agg(h)).collect();
        let ctot: f64 = wc.iter().sum();
        let pr = if iraise.is_empty() || ctot <= 0.0 { vec![0f64; nh] } else { fill(&ag, &wc, (rt / (1.0 - ft as f64).max(1e-6)).min(1.0)) };
        for h in 0..nh {
            out[fi * nh + h] = (1.0 - pc[h]) as f32 + 1e-7;
            let rmass = pc[h] * pr[h];
            out[ipass * nh + h] = (pc[h] - rmass) as f32 + 1e-7;
            let a = agg(h);
            for (k, &i) in iraise.iter().enumerate() {
                let share = if a > 1e-6 { (s[i * nh + h] / a) as f64 } else { mix_avg[k] };
                out[i * nh + h] = (rmass * share) as f32;
            }
        }
    } else if let Some(bt) = lk.bet {
        let ag: Vec<f32> = (0..nh).map(|h| agg(h)).collect();
        let pb = fill(&ag, &w, bt as f64);
        // pool sizing split (same for every hand) if given
        let labels = act_labels(g);
        let tgt: Option<Vec<f64>> = lk.sizes.as_ref().and_then(|sz| {
            let pcts: Vec<(usize, f32, bool)> = iraise.iter().enumerate().map(|(k, &i)| { let l = &labels[i]; (k, if l == "a" { 1000.0 } else { l[1..].parse::<f32>().unwrap_or(100.0) }, l == "a") }).collect();
            if pcts.is_empty() { return None; }
            let mut m = vec![0f64; iraise.len()];
            for &(mid, mass) in sz {
                let k = if mid > 110.0 && pcts.iter().any(|p| p.2) { pcts.iter().find(|p| p.2).unwrap().0 } else {
                    pcts.iter().filter(|p| !p.2).min_by(|a, b| (a.1 / mid).ln().abs().partial_cmp(&(b.1 / mid).ln().abs()).unwrap()).map(|p| p.0).unwrap_or(pcts[0].0) };
                m[k] += mass as f64;
            }
            let t: f64 = m.iter().sum(); if t > 0.0 { Some(m.iter().map(|x| x / t).collect()) } else { None }
        });
        if let Some(tg) = tgt {
            for h in 0..nh {
                out[ipass * nh + h] = (1.0 - pb[h]) as f32 + 1e-7;
                for (k, &i) in iraise.iter().enumerate() { out[i * nh + h] = (pb[h] * tg[k]) as f32 + 1e-9; }
            }
            return out;
        }
        for h in 0..nh {
            out[ipass * nh + h] = (1.0 - pb[h]) as f32 + 1e-7;
            let a = agg(h);
            for (k, &i) in iraise.iter().enumerate() {
                let share = if a > 1e-6 { (s[i * nh + h] / a) as f64 } else { mix_avg[k] };
                out[i * nh + h] = (pb[h] * share) as f32;
            }
        }
    } else { return s; }
    out
}

fn lock_rec(g: &mut PostFlopGame, c: &mut Ctx, villain: usize, reach: Vec<f32>, locks: &[(regex::Regex, Lock)], stats: &mut HashMap<String, (u32, f64, f64, f64)>) {
    if g.is_terminal_node() { return; }
    if g.is_chance_node() {
        let cards: Vec<u8> = g.available_actions().iter().filter_map(|a| if let Action::Chance(x) = a { Some(*x) } else { None }).collect();
        let hands = g.private_cards(villain).to_vec();
        for cd in cards {
            let mut r2 = reach.clone();
            for (h, &(a, b)) in hands.iter().enumerate() { if a == cd || b == cd { r2[h] = 0.0; } }
            let hist = g.history().to_vec();
            g.play(cd as usize); c.line.push("/".into());
            lock_rec(g, c, villain, r2, locks, stats);
            c.line.pop(); g.apply_history(&hist);
        }
        return;
    }
    let labels = act_labels(g);
    let p = g.current_player();
    let mut strat: Option<Vec<f32>> = None;
    if p == villain {
        let ls = line_str(c);
        for (re, lk) in locks {
            if re.is_match(&ls) {
                let st = make_lock(g, lk, &reach);
                // stats: observed fold / agg freq after lock
                let nh = reach.len(); let tot: f64 = reach.iter().map(|&x| x as f64).sum();
                let mut fsum = 0.0; let mut asum = 0.0;
                for h in 0..nh { let rs: f32 = (0..labels.len()).map(|i| st[i * nh + h]).sum(); for (i, l) in labels.iter().enumerate() { let v = (reach[h] * st[i * nh + h] / rs.max(1e-9)) as f64; if l == "f" { fsum += v; } if l.starts_with('b') || l.starts_with('r') || l == "a" { asum += v; } } }
                let e = stats.entry(lk.pat.clone()).or_insert((0, 0.0, 0.0, 0.0));
                e.0 += 1; e.1 += tot; e.2 += fsum; e.3 += asum;
                g.lock_current_strategy(&st);
                strat = Some(st);
                break;
            }
        }
    }
    let nh = g.private_cards(villain).len();
    let s = if p == villain { Some(strat.unwrap_or_else(|| g.strategy())) } else { None };
    let hist = g.history().to_vec();
    for (i, l) in labels.iter().enumerate() {
        let r2: Vec<f32> = if let Some(ref s) = s { (0..nh).map(|h| { let tot: f32 = (0..labels.len()).map(|k| s[k * nh + h]).sum(); reach[h] * s[i * nh + h] / tot.max(1e-9) }).collect() } else { reach.clone() };
        g.play(i); c.line.push(l.clone());
        lock_rec(g, c, villain, r2, locks, stats);
        c.line.pop(); g.apply_history(&hist);
    }
}

fn r4(x: f32) -> f64 { ((x as f64) * 10000.0).round() / 10000.0 }

fn dump_node(g: &mut PostFlopGame, c: &Ctx, raw: bool) -> Value {
    g.cache_normalized_weights();
    let p = g.current_player();
    let labels = act_labels(g);
    let s = g.strategy(); let ev = g.expected_values_detail(p); let eq = g.equity(p);
    let w0 = g.normalized_weights(0).iter().map(|&x| r4(x)).collect::<Vec<_>>();
    let w1 = g.normalized_weights(1).iter().map(|&x| r4(x)).collect::<Vec<_>>();
    let (pot, b) = node_pot(g);
    json!({"line": line_str(c), "player": p, "acts": labels, "pot": pot, "bets": b, "board": g.current_board().iter().map(|&x| card_str(x)).collect::<String>(),
           "strat": s.iter().map(|&x| r4(x)).collect::<Vec<_>>(), "ev": ev.iter().map(|&x| ((x as f64)*100.0).round()/100.0).collect::<Vec<_>>(),
           "eq": eq.iter().map(|&x| r4(x)).collect::<Vec<_>>(), "w": [w0, w1],
           "wr": if raw { json!([g.weights(0).iter().map(|&x| ((x as f64)*1e5).round()/1e5).collect::<Vec<_>>(), g.weights(1).iter().map(|&x| ((x as f64)*1e5).round()/1e5).collect::<Vec<_>>()]) } else { Value::Null }})
}

fn dump_street(g: &mut PostFlopGame, c: &mut Ctx, out: &mut Vec<Value>, street_only: bool, raw: bool) {
    if g.is_terminal_node() || g.is_chance_node() { return; }
    out.push(dump_node(g, c, raw));
    if !street_only { return; }
    let labels = act_labels(g); let hist = g.history().to_vec();
    for (i, l) in labels.iter().enumerate() {
        g.play(i); c.line.push(l.clone());
        dump_street(g, c, out, true, false);
        c.line.pop(); g.apply_history(&hist);
    }
}

fn main() {
    let path = std::env::args().nth(1).expect("job.json");
    let job: Job = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    let t0 = Instant::now();
    let mkr = |s: &String, w: &Vec<(String, f32)>| -> Range {
        if w.is_empty() { return s.parse().unwrap(); }
        let hands: Vec<(u8, u8)> = w.iter().map(|(h, _)| (card_from_str(&h[0..2]).unwrap(), card_from_str(&h[2..4]).unwrap())).collect();
        let ws: Vec<f32> = w.iter().map(|x| x.1.clamp(0.0, 1.0)).collect();
        Range::from_hands_weights(&hands, &ws).unwrap()
    };
    let turn_card = job.turn.as_ref().map(|t| card_from_str(t).unwrap()).unwrap_or(NOT_DEALT);
    let card_config = CardConfig { range: [mkr(&job.oop, &job.oop_w), mkr(&job.ip, &job.ip_w)], flop: flop_from_str(&job.flop).unwrap(), turn: turn_card, river: NOT_DEALT };
    let bs = |a: &str, r: &str| BetSizeOptions::try_from((a, r)).unwrap();
    let tree_config = TreeConfig {
        initial_state: if turn_card == NOT_DEALT { BoardState::Flop } else { BoardState::Turn }, starting_pot: job.pot, effective_stack: job.stack, rake_rate: job.rake_rate, rake_cap: job.rake_cap,
        flop_bet_sizes: [bs(&job.flop_oop, &job.flop_raise), bs(&job.flop_ip, &job.flop_raise)],
        turn_bet_sizes: [bs(&job.turn_oop, &job.turn_raise), bs(&job.turn_ip, &job.turn_raise)],
        river_bet_sizes: [bs(&job.river_oop, &job.river_raise), bs(&job.river_ip, &job.river_raise)],
        turn_donk_sizes: job.turn_donk.as_ref().map(|s| DonkSizeOptions::try_from(s.as_str()).unwrap()),
        river_donk_sizes: job.river_donk.as_ref().map(|s| DonkSizeOptions::try_from(s.as_str()).unwrap()),
        add_allin_threshold: 1.5, force_allin_threshold: 0.15, merging_threshold: 0.1,
    };
    let mut tree = ActionTree::new(tree_config).unwrap();
    prune(&mut tree, 0);
    tree.back_to_root();
    if job.root_no_bet {
        let acts: Vec<Action> = tree.available_actions().to_vec();
        for a in acts { if matches!(a, Action::Bet(_) | Action::AllIn(_)) { tree.remove_action(a).unwrap(); } }
        tree.back_to_root();
    }
    let mut game = PostFlopGame::with_config(card_config, tree).unwrap();
    let (m, mc) = game.memory_usage();
    eprintln!("mem {:.2}GB (compressed {:.2}GB) hands {} {}", m as f64 / 1e9, mc as f64 / 1e9, game.private_cards(0).len(), game.private_cards(1).len());
    if std::env::var("MEMONLY").is_ok() { return; }
    game.allocate_memory(job.compress);
    let pot = job.pot as f32;
    let mut it = 0u32; let mut expl;
    let mut info = json!({});
    let check_every = 10;
    let stage_target = if job.hero.is_some() { job.rank_pct.unwrap_or(1.5) } else { job.target_pct };
    loop {
        solve_step(&game, it); it += 1;
        if it % check_every == 0 || it >= job.iters {
            expl = compute_exploitability(&game) / pot * 100.0;
            if expl <= stage_target || it >= job.iters { break; }
        }
    }
    eprintln!("stage1 it {} expl {:.3}% t {:.1}s", it, expl, t0.elapsed().as_secs_f32());
    info["gto_iters"] = json!(it); info["gto_expl_pct"] = json!(expl);
    let ev_eq = compute_current_ev(&game);
    info["ev_eq"] = json!([ev_eq[0], ev_eq[1]]);
    if let Some(hero) = job.hero {
        let villain = 1 - hero;
        let locks: Vec<(regex::Regex, Lock)> = job.locks.iter().map(|l| (regex::Regex::new(&l.pat).unwrap(), l.clone())).collect();
        let mut stats = HashMap::new();
        let mut c = Ctx { line: job.line0.clone() };
        game.back_to_root();
        let r0 = game.initial_weights(villain).to_vec();
        lock_rec(&mut game, &mut c, villain, r0, &locks, &mut stats);
        game.back_to_root();
        let ev_gto_vs_pool = compute_current_ev(&game);
        info["ev_gto_vs_pool"] = json!([ev_gto_vs_pool[0], ev_gto_vs_pool[1]]);
        info["lock_stats"] = json!(stats.iter().map(|(k, v)| (k.clone(), json!({"nodes": v.0, "fold": if v.1>0.0 {v.2/v.1} else {0.0}, "agg": if v.1>0.0 {v.3/v.1} else {0.0}}))).collect::<HashMap<_,_>>());
        eprintln!("locked {} patterns t {:.1}s", stats.len(), t0.elapsed().as_secs_f32());
        // continue: hero best-responds (villain unlocked nodes also adapt)
        let mut gap;
        let it0 = it;
        loop {
            solve_step(&game, it); it += 1;
            if (it - it0) % check_every == 0 || it >= job.iters + it0 {
                let mes = compute_mes_ev(&game); let cur = compute_current_ev(&game);
                gap = (mes[hero] - cur[hero]) / pot * 100.0;
                if gap <= job.target_pct || it >= job.iters + it0 { break; }
            }
        }
        let cur = compute_current_ev(&game);
        info["hero_gap_pct"] = json!(gap); info["ev_exploit"] = json!([cur[0], cur[1]]); info["iters_total"] = json!(it);
        eprintln!("stage2 it {} hero gap {:.3}% t {:.1}s", it, gap, t0.elapsed().as_secs_f32());
    }
    finalize(&mut game);
    // extraction
    let mut nodes = vec![];
    for ex in &job.extract {
        game.back_to_root();
        let mut c = Ctx { line: job.line0.clone() };
        let mut ok = true;
        for tok in &ex.prefix {
            if game.is_terminal_node() { ok = false; break; }
            if game.is_chance_node() {
                let cd = card_from_str(tok).unwrap();
                if game.possible_cards() & (1u64 << cd) == 0 { ok = false; break; }
                game.play(cd as usize); c.line.push("/".into());
            } else {
                let labels = act_labels(&game);
                match labels.iter().position(|l| l == tok) { Some(i) => { game.play(i); c.line.push(tok.clone()); } None => { ok = false; break; } }
            }
        }
        if !ok { continue; }
        dump_street(&mut game, &mut c, &mut nodes, ex.street, ex.raw);
    }
    game.back_to_root();
    let hands: Vec<Vec<String>> = (0..2).map(|p| game.private_cards(p).iter().map(|&(a, b)| format!("{}{}", card_str(b), card_str(a))).collect()).collect();
    info["secs"] = json!(t0.elapsed().as_secs_f32());
    let out = json!({"flop": job.flop, "pot": job.pot, "stack": job.stack, "info": info, "hands": hands, "nodes": nodes});
    std::fs::write(&job.out, serde_json::to_string(&out).unwrap()).unwrap();
    eprintln!("done {:.1}s nodes {}", t0.elapsed().as_secs_f32(), out["nodes"].as_array().unwrap().len());
}
