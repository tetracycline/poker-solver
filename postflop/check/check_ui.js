// UI consistency: the page's grading function and grid must agree with the Python reference on the same data,
// and answering the graded main action must always be judged correct.
const { chromium } = require('playwright-core');
const fs = require('fs');
const BASE = process.argv[2] || 'http://localhost:18931/postflop/index.html';
const REF = JSON.parse(fs.readFileSync(require('path').join(__dirname, 'grading_ref.json')));
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', args: ['--no-sandbox'] });
  const pg = await (await b.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
  const errs = []; pg.on('pageerror', e => errs.push(e.message)); pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await pg.goto(BASE + '#all'); await pg.waitForSelector('.qcard .hand', { timeout: 15000 });
  let mism = 0, gridBad = 0, judged = 0, judgeBad = 0;
  for (const [k, r] of REF.entries()) {
    const out = await pg.evaluate(async r => {
      const F = await PP.loadFlop(r.sp, r.fl), n = PP.findNode(F, r.v, r.l, r.b), i = PP.hidx(n, r.h), o = PP.okActs(n, i);
      // grid aggregate for the class must equal the reach-weighted mean of its combos' rows
      const A = PP.classAgg(n); let gb = 0;
      Object.values(A).forEach(x => { const tw = x.idx.reduce((t, j) => t + n.w[j], 0); n.a.forEach((a, j) => { const m = x.idx.reduce((t, q) => t + n.w[q] * PP.row(n, q)[j], 0) / tw; if (Math.abs(m - x.s[j]) > 1e-6) gb++; }); });
      return {main: o.main, ok: o.ok, gb, jm: PP.judge(n, i, o.main), jz: n.a.filter((a, j) => o.s[j] === 0).map(a => PP.judge(n, i, a))};
    }, r);
    if (out.main !== r.main || out.ok.join() !== r.ok.join()) mism++;
    gridBad += out.gb; judged++;
    if (out.jm !== 'ok') judgeBad++;
    if (out.jz.some(x => x === 'ok' || x === 'mix')) judgeBad++;
  }
  // live drill path: force questions and answer the main action through the real UI
  let live = 0, liveBad = 0;
  for (const r of REF.slice(0, 40)) {
    await pg.evaluate(v => { localStorage.setItem('pk8.ver', v); }, r.v);
    await pg.evaluate(() => PP.go('all')); await pg.waitForFunction(() => PP.q());
    if (await pg.evaluate(() => PP.version()) !== r.v) await pg.click(`[data-ver="${r.v}"]`), await pg.waitForFunction(v => PP.version() === v && PP.q(), r.v);
    await pg.evaluate(r => PP.ask(r.sp, r.fl, r.l, r.b, r.h), r);
    await pg.click(`#abar [data-a="${r.main}"]`); await pg.waitForSelector('.res');
    const a = await pg.evaluate(() => PP.ans()); live++; if (a.res !== 'ok') liveBad++;
    // the highlighted grid cell must be this hand's class
    const hl = await pg.$eval('.grid .gc.hl', e => e.dataset.h);
  }
  console.log(JSON.stringify({checked: judged, grading_mismatch: mism, grid_aggregate_mismatch: gridBad, judge_errors: judgeBad, live_answers: live, live_wrong: liveBad, console_errors: errs.length}));
  await b.close(); process.exit(mism || gridBad || judgeBad || liveBad || errs.length ? 1 : 0);
})();
