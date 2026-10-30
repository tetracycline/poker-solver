// Pack preflop GTO/exploit + river spot library into data/bundle.js for the drill page (works from file://).
const fs = require('fs');
const G = JSON.parse(fs.readFileSync('preflop/gto_rake.json')), GN = JSON.parse(fs.readFileSync('preflop/gto_norake.json'));
const E = JSON.parse(fs.readFileSync('preflop/exploit_rake.json'));
const pct = a => a.map(x => Math.round(x * 100));
function packNode(v) { return { acts: v.acts, freq: Object.fromEntries(Object.entries(v.freq).map(([a, x]) => [a, Math.round(x * 1000) / 10])), s: v.strat.map(pct), r: pct(v.reach) }; }
const pre = { names: G.names, gto: {}, norake: {}, exp: {}, pool: E.pool_info, heroes: {}, params: G.meta.params, iters: G.meta.iters, hist: G.meta.hist };
for (const k in G.nodes) { pre.gto[k] = Object.assign({ seat: G.nodes[k].seat }, packNode(G.nodes[k])); pre.norake[k] = { freq: packNode(GN.nodes[k]).freq }; }
for (const h in E.heroes) { const x = E.heroes[h]; pre.heroes[h] = { ev_exploit: x.ev_exploit, ev_gto_vs_pool: x.ev_gto_vs_pool, gain_bb100: x.gain_bb100 }; for (const k in x.nodes) pre.exp[k] = packNode(x.nodes[k]); }
const spots = fs.readdirSync('data/spots').sort().map(f => JSON.parse(fs.readFileSync('data/spots/' + f)));
const order = ['BTN_BB_bb', 'BTN_BB_bx', 'BTN_BB_xx', 'CO_BB_bb', 'SB_BB_bb', 'SB_BB_bx', 'BB3_BTN_bx', 'BB3_BTN_bb'];
spots.sort((a, b) => order.indexOf(a.fam) - order.indexOf(b.fam) || a.id.localeCompare(b.id));
const out = 'window.SOLVER_DATA=' + JSON.stringify({ built: new Date().toISOString(), pre, spots }) + ';';
fs.writeFileSync('data/bundle.js', out);
console.log('bundle', (out.length / 1e6).toFixed(2), 'MB', spots.length, 'spots', Object.keys(pre.gto).length, 'preflop nodes');
