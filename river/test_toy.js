// Validation (b): clairvoyance / polarized river game. OOP: 50% nuts, 50% air; IP: only bluff-catchers. OOP bet s*pot, IP fold/call.
const RS = require('./river.js');
function toy(s, nHands = 60) {
  const oop = [], ip = [];
  for (let i = 0; i < nHands; i++) oop.push({ c1: -1, c2: -1, w: 1, r: i < nHands / 2 ? 100 : 1, tag: i < nHands / 2 ? 'nuts' : 'air' });
  for (let i = 0; i < nHands; i++) ip.push({ c1: -1, c2: -1, w: 1, r: 50, tag: 'bc' });
  const sv = new RS.Solver({ board: [], ranges: [oop, ip], pot: 1, stack: 100, oopBets: [s], ipBets: [], raises: [], maxRaises: 0, allinThreshold: 2 });
  sv.solve({ iters: 4000, check: 200, target: 0.01 });
  const rep = sv.report(); const r0 = rep[0];
  // bluff ratio among bets
  let vb = 0, bb = 0; const H = sv.g.H[0];
  const bi = r0.acts.findIndex(a => a.k === 'B');
  H.forEach((h, i) => { if (h.tag === 'nuts') vb += r0.S[bi][i]; else bb += r0.S[bi][i]; });
  const facing = rep.find(x => x.pl === 1 && x.acts.some(a => a.k === 'C'));
  const ci = facing.acts.findIndex(a => a.k === 'C');
  const ex = sv.exploitability();
  return { s, bluffRatio: bb / (vb + bb), theoryBluff: s / (1 + 2 * s), call: facing.freq[ci], theoryMDF: 1 / (1 + s), exploitPct: ex.exploitPct, iters: sv.it,
           oopEV: ex.ev[0], theoryOopEV: 0.5 * 1 + 0.5 * 1 * (s / (1 + s)) * 1 /* value: wins pot+bet*call... computed below */ };
}
const out = [];
for (const s of [0.33, 0.5, 0.75, 1.0, 1.5, 2.0]) {
  const r = toy(s);
  // theory OOP EV (pot=1): nuts bet: called with prob q=1/(1+s): win 1+s, else 1 ; air: bluffs b fraction earn 0 EV (indifferent) -> equals check EV 0.
  const q = 1 / (1 + s); r.theoryOopEV = 0.5 * (q * (1 + s) + (1 - q) * 1);
  out.push(r);
  console.log(`s=${s}: bluff ratio ${r.bluffRatio.toFixed(4)} (theory ${r.theoryBluff.toFixed(4)}), IP call ${r.call.toFixed(4)} (MDF ${r.theoryMDF.toFixed(4)}), OOP EV ${r.oopEV.toFixed(4)} (theory ${r.theoryOopEV.toFixed(4)}), exploitability ${r.exploitPct.toFixed(4)}% pot @${r.iters} it`);
}
require('fs').writeFileSync(__dirname + '/../data/validation_toy.json', JSON.stringify(out, null, 1));
