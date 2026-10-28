#!/usr/bin/env node
// Screenshots the client sites Dorien built, for the intro's card stack.
// Usage: node shoot_sites.cjs [workdir]  → WORK/intro/site-<n>.png
const path = require('path');
const puppeteer = require('/Users/dorienvandenabbeele/Documents/antigravity/noble-pythagoras/node_modules/puppeteer-core');
const WORK = process.argv[2] || path.join(process.env.HOME, 'Desktop', 'Lucienne_Video', 'v3_work');
const SITES = ['https://panacacao.com/', 'https://finca-montezuma.com/', 'https://bocasnaturetours.com/'];
(async () => {
  const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: 'new', args: ['--no-sandbox'] });
  for (const [i, url] of SITES.entries()) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 2500));  // hero fades and lazy images
    await page.screenshot({ path: path.join(WORK, 'intro', `site-${i + 1}.png`) });
    console.log('✓', url);
    await page.close();
  }
  await browser.close();
})();
