// Precompute river spot library: GTO + pool-node-locked exploit versions.
const fs = require('fs');
const RS = require('./river.js'), RG = require('./ranges.js');
const PF = JSON.parse(fs.readFileSync(__dirname + '/../preflop/gto_rake.json'));
const RB = JSON.parse(fs.readFileSync(__dirname + '/../inputs/river_bluff.json'));
const PS = JSON.parse(fs.readFileSync(__dirname + '/../inputs/pool_stats.json')).NL2;
const C = s => s.match(/../g).map(RS.card);
const BOARDS = {
  b1: { cards: 'As7d2c9h4s', tex: 'A高乾燥・河牌空白' },
  b2: { cards: 'KhQd6s2cJh', tex: '高張連接・河牌補順' },
  b3: { cards: '9s8s4dKc2s', tex: '濕潤・河牌同花完成' },
  b4: { cards: 'JcJd5h3s8c', tex: '對子面・河牌空白' },
  b5: { cards: '7h6h2dTs9c', tex: '低連接・河牌補順' },
  b6: { cards: 'Qc7c3s3dAc', tex: '轉牌成對・河牌A同花完成' },
  b7: { cards: 'Td9c4h2s2h', tex: '河牌成對（空白）' },
  b8: { cards: 'Ks8h5c5dKd', tex: '雙對子面' },
};
// families: agg = preflop aggressor, def = caller. oop index 0.
const FAM = {
  BTN_BB_bb: { pre: 'BTNvsBB', line: 'bb', boards: ['b1','b2','b3','b4','b5','b6','b7','b8'] },
  BTN_BB_bx: { pre: 'BTNvsBB', line: 'bx', boards: ['b1','b2','b3','b4','b5','b6','b7','b8'] },
  CO_BB_bb:  { pre: 'COvsBB', line: 'bb', boards: ['b1','b2','b3','b5','b7','b8'] },
  BTN_BB_xx: { pre: 'BTNvsBB', line: 'xx', boards: ['b1','b3','b4','b6','b7','b8'] },
  SB_BB_bb:  { pre: 'SBvsBB', line: 'bb', boards: ['b1','b2','b4','b5','b6'] },
  SB_BB_bx:  { pre: 'SBvsBB', line: 'bx', boards: ['b2','b3','b5','b7','b8'] },
  BB3_BTN_bx: { pre: 'BB3vsBTN', line: 'bx', boards: ['b1','b2','b5'] },
  BB3_BTN_bb: { pre: 'BB3vsBTN', line: 'bb', boards: ['b3','b6','b8'] },
};
const PRE = {
  BTNvsBB: { agg: 'BTN', def: 'BB', aggIP: true, P0: 5.5, S0: 97.5, pt: 'SRP', agR: [['BTNrfi','open']], deR: [['BTNopen>BB','call']] },
  COvsBB:  { agg: 'CO', def: 'BB', aggIP: true, P0: 5.5, S0: 97.5, pt: 'SRP', agR: [['COrfi','open']], deR: [['COopen>BB','call']] },
  SBvsBB:  { agg: 'SB', def: 'BB', aggIP: false, P0: 6, S0: 97, pt: 'SRP', agR: [['SBrfi','open']], deR: [['SBopen>BB','call']] },
  BB3vsBTN: { agg: 'BB', def: 'BTN', aggIP: false, P0: 20.5, S0: 90, pt: '3BP', agR: [['BTNopen>BB','3bet']], deR: [['BTNrfi','open'],['BTNopen>BB3b','call']] },
};
const LINE_TXT = { bb: '翻牌 c-bet 33% 被跟 → 轉牌 75% 再開槍被跟', bx: '翻牌 c-bet 33% 被跟 → 轉牌雙方過牌', xx: '翻牌、轉牌雙方都過牌' };
const TRAP_KEEP = 0.8;   // pool checks ~20% of its value range on the river (no pool data on river check-raise ranges; HU street-3 x/r freq is 3.8%)
const r2 = x => Math.round(x * 100) / 100;

function buildRanges(pre, line, board) {
  const fl = board.slice(0, 3), tu = board.slice(0, 4);
  let A = RG.removeDead(RG.fromPreflop(PF, pre.agR), board), D = RG.removeDead(RG.fromPreflop(PF, pre.deR), board);
  let pot = pre.P0, st = pre.S0;
  if (line === 'xx') {                  // aggressor checks back flop & turn (IP) / both check (OOP agg)
    A = RG.splitBarrel(A, fl, 0.45, 0.15)[1];
    A = RG.splitBarrel(A, tu, 0.45, 0.15)[1];
    D = RG.splitBarrel(D, tu, 0.55, 0.12)[1];   // defender also declined to stab turn
  } else {
    A = RG.splitBarrel(A, fl, 0.6, 0.2)[0]; D = RG.keepTop(D, fl, 0.72);
    const b = 0.33 * pot; pot += 2 * b; st -= b;
    if (line === 'bb') { A = RG.splitBarrel(A, tu, 0.45, 0.12)[0]; D = RG.keepTop(D, tu, 0.58); const t = 0.75 * pot; pot += 2 * t; st -= t; }
    else { A = RG.splitBarrel(A, tu, 0.45, 0.12)[1]; if (!pre.aggIP) D = RG.splitBarrel(D, tu, 0.55, 0.12)[1]; }
  }
  return { A, D, pot: r2(pot), stack: r2(st) };
}
function bucket(f) { const p = f * 100; return p <= 25 ? '≤25%' : p <= 40 ? '26-40%' : p <= 55 ? '41-55%' : p <= 70 ? '56-70%' : p <= 90 ? '71-90%' : p <= 110 ? '91-110%' : p <= 150 ? '111-150%' : '>150%'; }
function poolResp(line, frac) {
  const k = line + ' | ' + bucket(frac), x = RB.by_line_size[k];
  if (x && x.n >= 300) return { fold: x.fold / 100, rz: x.rz / 100, n: x.n, src: 'by_line_size[' + k + ']' };
  const o = RB.overall_by_size ? RB.overall_by_size[bucket(frac)] : null;
  if (o) return { fold: o.fold / 100, rz: (o.rz || 5) / 100, n: o.n, src: 'overall_by_size[' + bucket(frac) + ']' };
  return null;
}
// lock: rank-ordered: top rz -> raise (if available), next -> call, bottom fold, using GTO reach at node
function respLock(s, node, reach, pr) {
  const p = node.pl, H = s.g.H[p], N = H.length, A = node.acts.length;
  const idx = H.map((_, i) => i).sort((a, b) => H[b].r - H[a].r);
  const tot = reach.reduce((x, y) => x + y, 0); const S = []; for (let a = 0; a < A; a++) S.push(new Float64Array(N));
  const iF = node.acts.findIndex(x => x.k === 'F'), iC = node.acts.findIndex(x => x.k === 'C'), iR = node.acts.findIndex(x => x.k === 'R');
  const rz = iR >= 0 ? pr.rz : 0, callF = 1 - pr.fold - rz; let acc = 0;
  idx.forEach(i => {
    const lo = acc / tot, hi = (acc + reach[i]) / tot; acc += reach[i];
    const seg = (a, b) => Math.max(0, Math.min(hi, b) - Math.max(lo, a)) / Math.max(hi - lo, 1e-12);
    const fr = seg(0, rz), fc = seg(rz, rz + callF), ff = 1 - fr - fc;
    if (hi - lo < 1e-12) { S[iF][i] = 1; return; }
    S[iF][i] = ff; S[iC][i] = fc; if (iR >= 0) S[iR][i] = fr;
  });
  return S;
}
// pool bettor (double-barrel line): bet freq fb, air share among bets ab, all on the size closest to 75%
function betLock(s, node, reach, fb, ab) {
  const p = node.pl, H = s.g.H[p], N = H.length, A = node.acts.length;
  let ib = -1, bd = 9; node.acts.forEach((x, a) => { if (x.k === 'B' && Math.abs(x.frac - 0.75) < bd) { bd = Math.abs(x.frac - 0.75); ib = a; } });
  const idx = H.map((_, i) => i).sort((a, b) => H[b].r - H[a].r), tot = reach.reduce((x, y) => x + y, 0);
  const vTop = fb * (1 - ab), bBot = fb * ab; const S = []; for (let a = 0; a < A; a++) S.push(new Float64Array(N)); let acc = 0;
  idx.forEach(i => { const lo = acc / tot, hi = (acc + reach[i]) / tot; acc += reach[i];
    const seg = (a, b) => Math.max(0, Math.min(hi, b) - Math.max(lo, a)) / Math.max(hi - lo, 1e-12);
    // value hands bet with prob TRAP_KEEP (the rest are checked = traps), so the value band is widened to keep the total
    const f = hi - lo < 1e-12 ? 0 : TRAP_KEEP * seg(0, Math.min(1, vTop / TRAP_KEEP)) + seg(1 - bBot, 1); S[ib][i] = Math.min(1, f); S[0][i] = 1 - Math.min(1, f); });
  return { S, size: node.acts[ib].frac };
}
function packNodes(s, rep, ev, keep) {
  return rep.filter(n => keep(n)).map(n => {
    const H = s.g.H[n.pl]; const tot = n.reach.reduce((a, b) => a + b, 0);
    const hands = []; H.forEach((h, i) => { if (n.reach[i] / (s.w[n.pl][i] || 1) > 0.01 && n.reach[i] > 1e-6) hands.push(i); });
    return { id: n.id, hist: n.hist, pl: n.pl, acts: n.acts.map(a => a.label + (a.frac ? ' ' + Math.round(a.frac * 100) + '%' : '') + (a.to ? '|' + a.to : '')),
      freq: n.freq.map(x => r2(x)), rw: r2(tot), c: n.c,
      h: hands, r: hands.map(i => r2(n.reach[i])), S: hands.map(i => n.acts.map((_, a) => Math.round(n.S[a][i] * 100))),
      ev: hands.map(i => n.acts.map((_, a) => ev[n.id][a][i] == null ? null : Math.round(ev[n.id][a][i] * 10) / 10)) };
  });
}

// per bet action: bettor freq, bluff ratio (share of bet combos with <50% equity vs the caller's continuing range), defender continue vs MDF
function betStats(s, rep) {
  const byHist = {}; rep.forEach(n => byHist[n.hist] = n); const out = [];
  rep.forEach(n => n.acts.forEach((a, k) => {
    if (a.k !== 'B') return; const kid = byHist[n.hist + (a.label === 'allin' ? 'A' : 'B') + Math.round(a.frac * 100)]; if (!kid) return;
    const p = n.pl, q = 1 - p, iF = kid.acts.findIndex(x => x.k === 'F');
    const bet = n.reach.map((r, i) => r * n.S[k][i]); const btot = bet.reduce((x, y) => x + y, 0); if (btot < 1e-6) return;
    const cont = kid.reach.map((r, i) => r * (1 - kid.S[iF][i]));
    const sd = s.term({ t: 's', c: [0, 0] }, p, Float64Array.from(cont)), ct = new Float64Array(bet.length); RS.compatTot(s.g, p, Float64Array.from(cont), ct);
    let bl = 0; bet.forEach((w, i) => { if (ct[i] > 1e-9 && sd[i] / (s.spec.pot * ct[i]) < 0.5) bl += w; });
    const sz = (a.to - n.c[p]) / (s.spec.pot + n.c[0] + n.c[1]);
    out.push({ node: n.hist || 'root', pl: p, size: r2(sz), betFreq: r2(n.freq[k]), bluffRatio: r2(bl / btot), theoryBluff: r2(sz / (1 + 2 * sz)), defCont: r2(1 - kid.freq[iF]), MDF: r2(1 / (1 + sz)) });
  }));
  return out;
}
const keepNode = n => n.hist.replace(/\d+/g, '').length <= 2 && n.reachW > 1e-3 && n.reachOpp > 1e-3;
function mkSpec(R, board) {
  return { board, pot: R.pot, stack: R.stack, oopBets: [0.33, 0.75, 1.5, 'allin'], ipBets: [0.33, 0.75, 1.5, 'allin'], raises: [1.0], maxRaises: 1, allinThreshold: 0.67 };
}
function solveSpot(fid, bid) {
  const F = FAM[fid], pre = PRE[F.pre], board = C(BOARDS[bid].cards);
  const R = buildRanges(pre, F.line, board);
  const oopIsAgg = !pre.aggIP; const ranges = oopIsAgg ? [R.A, R.D] : [R.D, R.A];
  const spec = Object.assign(mkSpec(R, board), { ranges });
  const t0 = Date.now(); const s = new RS.Solver(spec); s.solve({ iters: 3000, check: 100, target: 0.1 });
  const ex = s.exploitability(); const rep = s.report(); const ev = s.nodeEVs();
  const aggP = oopIsAgg ? 0 : 1, defP = 1 - aggP;
  const pos = oopIsAgg ? [pre.agg, pre.def] : [pre.def, pre.agg];
  const out = { id: fid + '_' + bid, fam: fid, pre: F.pre, pt: pre.pt, line: F.line, lineTxt: LINE_TXT[F.line], tex: BOARDS[bid].tex,
    board: BOARDS[bid].cards, pot: R.pot, stack: R.stack, pos, agg: aggP,
    hands: [0, 1].map(p => s.g.H[p].map(h => RS.cstr(h.c1) + RS.cstr(h.c2))), w: [0, 1].map(p => s.g.H[p].map(h => r2(h.w))),
    val: { exploitPct: +ex.exploitPct.toFixed(3), iters: s.it, ev: ex.ev.map(r2), ms: Date.now() - t0 },
    gto: packNodes(s, rep, ev, keepNode), stats: betStats(s, rep), exploit: {} };
  // ---- exploit versions: pool player locked at nodes with data; hero re-solved ----
  const byId = {}; s.nodes.forEach(n => byId[n.id] = n); const repById = {}; rep.forEach(n => repById[n.id] = n);
  for (const hero of [0, 1]) {
    const pool = 1 - hero; const s2 = new RS.Solver(spec); const locks = []; const id2 = {}; s2.nodes.forEach(n => id2[n.id] = n);
    s.nodes.forEach(n => {
      if (n.pl !== pool || !repById[n.id]) return;
      const parentBet = n.hist.match(/(B|A)(\d+)$/);
      if (n.acts[0].k === 'F' && parentBet && !/R/.test(n.hist)) {
        const heroLine = hero === aggP ? F.line : (F.line === 'bb' ? 'cc' : F.line === 'bx' ? 'cx' : 'xx');
        const frac = parentBet[2] / 100; const pr = poolResp(heroLine, frac >= 2 ? 2.0 : frac);
        if (pr && frac > 2) {   // no reliable data for huge overbets: never assume the pool calls MORE than GTO there
          const g = repById[n.id]; const gf = g.freq[n.acts.findIndex(x => x.k === 'F')];
          if (gf > pr.fold) { pr.fold = gf; pr.src += ' (capped at GTO fold, size ' + Math.round(frac * 100) + '%)'; }
        }
        if (pr) { id2[n.id].lock = respLock(s, n, repById[n.id].reach, pr); locks.push({ node: n.hist, what: 'fold ' + Math.round(pr.fold * 100) + '% / raise ' + Math.round(pr.rz * 100) + '%', n: pr.n, src: pr.src }); }
      }
      if (pool === aggP && F.line === 'bb' && n.acts[0].k === 'X' && (n.hist === '' || n.hist === 'x')) {
        const st = PS.postflop_HU[pre.pt + (pre.aggIP ? '_PFR_IP' : '_PFR_OOP')];
        const fb = (st.river_barrel && st.river_barrel.pct || 47.8) / 100, ab = 0.206;
        const L = betLock(s, n, repById[n.id].reach, fb, ab); id2[n.id].lock = L.S;
        locks.push({ node: n.hist || 'root', what: 'bet ' + Math.round(fb * 100) + '% (' + Math.round(L.size * 100) + '% pot), air ' + Math.round(ab * 100) + '% of bets', n: st.river_barrel.n, src: 'postflop_HU.river_barrel + bettor_shown_called' });
      }
    });
    if (!locks.length) continue;
    s2.solve({ iters: 3000, check: 100, target: 0.1 });
    const e2 = s2.exploitability(), rep2 = s2.report(), ev2 = s2.nodeEVs();
    // hero GTO strategy vs the same locked pool (pool's unlocked nodes keep GTO)
    const s3 = new RS.Solver(spec); s3.nodes.forEach(n => { const o = id2[n.id]; if (o.lock) n.lock = o.lock; else n.lock = s.strat(byId[n.id], true); });
    const Z = s3.norm(); const vg = s3.val(s3.root, hero, s3.w[pool], false); let evG = 0; for (let i = 0; i < vg.length; i++) evG += s3.w[hero][i] * vg[i]; evG /= Z;
    out.exploit[hero] = { locks, heroEV: r2(e2.ev[hero]), heroEV_GTOvsPool: r2(evG), gainBB: r2(e2.ev[hero] - evG), gtoEV: r2(ex.ev[hero]), residualPct: +e2.exploitPct.toFixed(3),
      nodes: packNodes(s2, rep2, ev2, n => keepNode(n) && n.pl === hero) };
  }
  return out;
}
if (require.main === module) {
  const only = process.argv[2]; const index = [];
  for (const fid in FAM) for (const bid of FAM[fid].boards) {
    if (only && !(fid + '_' + bid).includes(only)) continue;
    const o = solveSpot(fid, bid); fs.writeFileSync(__dirname + '/../data/spots/' + o.id + '.json', JSON.stringify(o));
    index.push({ id: o.id, val: o.val, gain: [0, 1].map(p => o.exploit[p] ? o.exploit[p].gainBB : null), n: [o.hands[0].length, o.hands[1].length] });
    console.log(o.id, 'pot', o.pot, 'stk', o.stack, 'H', o.hands[0].length, o.hands[1].length, 'expl%', o.val.exploitPct, 'it', o.val.iters, o.val.ms + 'ms', 'gain', index[index.length - 1].gain);
  }
  if (!only) fs.writeFileSync(__dirname + '/../data/spots_index.json', JSON.stringify(index, null, 1));
}
module.exports = { solveSpot, buildRanges, FAM, PRE, BOARDS };
