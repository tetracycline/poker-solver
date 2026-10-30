const { chromium } = require('playwright-core');
const BASE = process.argv[2] || 'http://localhost:18931/postflop/index.html';
const OUT = process.argv[3] || require('path').join(__dirname, '../screens/');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', args: ['--no-sandbox'] });
  let errs = [];
  for (const [w, h, tag] of [[390, 844, 'm'], [1280, 900, 'd']]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: tag === 'm' ? 2 : 1 });
    const pg = await ctx.newPage();
    pg.on('pageerror', e => errs.push(tag + ' PAGEERR ' + e.message));
    pg.on('console', m => { if (m.type() === 'error') errs.push(tag + ' CONSOLE ' + m.text()); });
    await pg.goto(BASE + '#all'); await pg.waitForSelector('.qcard .hand', { timeout: 15000 });
    await pg.screenshot({ path: OUT + `${tag}_q_exp.png`, fullPage: tag === 'd' });
    // answer via bottom bar
    await pg.click('#abar .ab >> nth=0'); await pg.waitForSelector('.res');
    await pg.screenshot({ path: OUT + `${tag}_ans_exp.png`, fullPage: true });
    // drills by key, multiple pages
    const ids = await pg.evaluate(() => PP.drills().map(d => d.id));
    let n = 0;
    for (const id of ids) {
      await pg.evaluate(i => PP.go(i), id); await pg.waitForFunction(() => PP.q() || document.querySelector('#qbox').textContent.includes('沒有題目'), null, { timeout: 15000 });
      const q = await pg.evaluate(() => PP.q()); if (!q) continue;
      await pg.keyboard.press(['F', 'C', 'R'][n % 3]); await pg.waitForTimeout(30);
      if (!(await pg.evaluate(() => PP.ans()))) { await pg.click('#abar .ab >> nth=-1'); }
      await pg.waitForSelector('.res'); n++;
      if (id === 'BTN_BB.r_vs_bet' || id === 'BTN_BB.f_cbet' || id === 'SB3_BTN.f_cbet' || id === 'BB3_BTN.f_vs_cbet' || id === 'SB_BB.f_cbet' || id === 'BTN_BB.barrel') await pg.screenshot({ path: OUT + `${tag}_${id.replace('.', '_')}.png`, fullPage: true });
      await pg.keyboard.press(' '); await pg.waitForTimeout(30);
    }
    // gto toggle
    await pg.evaluate(() => PP.go('BTN_BB.f_vs_cbet')); await pg.waitForSelector('.qcard .hand');
    await pg.click('[data-ver="gto"]'); await pg.waitForFunction(() => PP.version() === 'gto' && PP.q());
    await pg.keyboard.press('C'); await pg.waitForSelector('.res');
    await pg.click('.grid .gc:not(.out) >> nth=3'); await pg.waitForTimeout(100);
    await pg.click('.cdet .cmb >> nth=0'); await pg.waitForTimeout(100);
    await pg.screenshot({ path: OUT + `${tag}_ans_gto.png`, fullPage: true });
    await pg.click('[data-ver="exp"]');
    // charts & about
    await pg.evaluate(() => PP.go('charts')); await pg.waitForSelector('#cbox .grid', { timeout: 15000 });
    await pg.screenshot({ path: OUT + `${tag}_charts.png`, fullPage: true });
    await pg.evaluate(() => PP.go('about')); await pg.waitForTimeout(200);
    await pg.screenshot({ path: OUT + `${tag}_about.png`, fullPage: true });
    console.log(tag, 'drills answered', n);
    await ctx.close();
  }
  console.log('errors', errs.length); errs.slice(0, 20).forEach(e => console.log(e));
  await b.close();
})();
