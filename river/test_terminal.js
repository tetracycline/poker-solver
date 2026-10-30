// Validation: O(N) showdown / fold evaluation vs naive O(N^2) with explicit card-removal, on random ranges & boards.
const RS = require('./river.js');
function rnd(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const R = rnd(7); let maxErr = 0;
for (let t = 0; t < 20; t++) {
  const deck = [...Array(52).keys()]; for (let i = 51; i > 0; i--) { const j = Math.floor(R() * (i + 1)); [deck[i], deck[j]] = [deck[j], deck[i]]; }
  const board = deck.slice(0, 5); const rest = deck.slice(5);
  const mk = () => { const a = []; for (let i = 0; i < rest.length; i++) for (let j = i + 1; j < rest.length; j++) if (R() < 0.3) a.push({ c1: rest[i], c2: rest[j], w: R() }); return a; };
  const g = RS.setup({ board, ranges: [mk(), mk()] });
  for (const p of [0, 1]) {
    const ro = Float64Array.from(g.H[1 - p].map(() => R()));
    const pot = 10, x = 3.7; const fast = new Float64Array(g.N[p]);
    // re-implement naive
    const sv = Object.create(RS.Solver.prototype); sv.g = g; sv.spec = { pot };
    const out = sv.term({ t: 's', c: [x, x] }, p, ro);
    const outF = sv.term({ t: 'f', winner: p, c: [x, 2 * x] }, p, ro);
    g.H[p].forEach((h, i) => {
      let v = 0, vf = 0;
      g.H[1 - p].forEach((o, j) => {
        if (o.c1 === h.c1 || o.c1 === h.c2 || o.c2 === h.c1 || o.c2 === h.c2) return;
        v += ro[j] * (h.r > o.r ? pot + x : h.r < o.r ? -x : pot / 2);
        vf += ro[j] * (pot + (p === 0 ? 2 * x : x));
      });
      maxErr = Math.max(maxErr, Math.abs(v - out[i]), Math.abs(vf - outF[i]));
    });
  }
}
console.log('max abs error fast vs naive terminal values:', maxErr.toExponential(2));
// evaluator sanity: category frequencies over random 7-card hands
const cnt = new Array(9).fill(0); const R2 = rnd(99); const n = 300000;
for (let t = 0; t < n; t++) { const s = new Set(); while (s.size < 7) s.add(Math.floor(R2() * 52)); cnt[RS.eval7([...s]) >> 20]++; }
console.log('7-card category freq:', cnt.map(c => (c / n).toFixed(4)).join(' '), '(expected .1741 .4382 .2350 .0483 .0462 .0303 .0260 .0017 .0003)');
