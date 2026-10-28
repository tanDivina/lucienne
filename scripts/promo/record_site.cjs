#!/usr/bin/env node
// Records Lucienne's landing page (local site/index.html, same as
// lucienne.hero-apps.com once deployed) per scene, timed to the narration:
// the hero with the lamplight following the pointer and the delight pose on
// the CTA hover, and the channels section. Writes WORK/site/<scene>.mp4.
// Usage: node record_site.cjs [workdir] [scene,scene...]
const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');
const puppeteer = require('/Users/dorienvandenabbeele/Documents/antigravity/noble-pythagoras/node_modules/puppeteer-core');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const FFMPEG = '/opt/homebrew/bin/ffmpeg';
const SITE = process.env.SITE_URL || 'file://' + path.join(__dirname, '..', '..', 'site', 'index.html');
const WORK = process.argv[2] || path.join(process.env.HOME, 'Desktop', 'Lucienne_Video', 'v3_work');
const OUT = path.join(WORK, 'site');
fs.mkdirSync(OUT, { recursive: true });
const only = process.argv[3] ? process.argv[3].split(',') : null;
const LEAD = 0.3;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dur = (f) => {
  try { return parseFloat(execSync(`/opt/homebrew/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "${f}"`).toString()); }
  catch { return 3; }
};
const AUDIO = path.join(process.env.HOME, 'Projects', 'lucienne', 'video', 'merge', 'audio');
const len = (line, pad = 1.0) => LEAD + dur(path.join(AUDIO, `${line}.mp3`)) + pad;

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new', protocolTimeout: 300000,
    args: ['--no-sandbox', '--disable-gpu', '--window-size=1600,940', '--force-device-scale-factor=1', '--autoplay-policy=no-user-gesture-required', '--mute-audio'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1.2 });
  // The site only wakes the toucan for a hover-capable pointer; headless has none.
  await page.evaluateOnNewDocument(() => {
    const mm = window.matchMedia.bind(window);
    window.matchMedia = (q) => (/hover:\s*hover|pointer:\s*fine/.test(q) ? { matches: true, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} } : mm(q));
  });

  // Each scene: fresh screencast into its own file, real time, with a heartbeat
  // pixel so idle stretches still produce frames (no clock drift).
  async function scene(name, seconds, run) {
    if (only && !only.includes(name)) return;
    const file = path.join(OUT, `${name}.mp4`);
    const ff = spawn(FFMPEG, ['-y', '-use_wallclock_as_timestamps', '1', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-i', '-',
      '-vf', 'scale=1920:1080:flags=lanczos', '-fps_mode', 'cfr', '-r', '30', '-t', seconds.toFixed(2),
      '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', file]);
    ff.stderr.on('data', () => {});
    ff.stdin.on('error', () => {});
    const closed = new Promise((r) => ff.on('close', r));
    const cdp = await page.target().createCDPSession();
    cdp.on('Page.screencastFrame', async ({ data, sessionId }) => {
      try { ff.stdin.write(Buffer.from(data, 'base64')); await cdp.send('Page.screencastFrameAck', { sessionId }); } catch {}
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, everyNthFrame: 1 });
    const t0 = Date.now();
    await run(() => (Date.now() - t0) / 1000);
    const left = seconds + 0.5 - (Date.now() - t0) / 1000;
    if (left > 0) await sleep(left * 1000);
    await cdp.send('Page.stopScreencast');
    await cdp.detach();
    ff.stdin.end();
    await closed;
    console.log(`✓ ${name}.mp4 (${seconds.toFixed(1)}s)`);
  }
  const at = async (now, t) => { const w = t - now(); if (w > 0) await sleep(w * 1000); };
  const scrollTo = (y, ms = 1400) => page.evaluate((target, d) => new Promise((done) => {
    const from = window.scrollY, delta = target - from, start = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - start) / d);
      const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      window.scrollTo(0, from + delta * e);
      k < 1 ? requestAnimationFrame(step) : done();
    };
    requestAnimationFrame(step);
  }), y, ms);
  const topOf = (sel, offset = 0) => page.evaluate((s, o) => {
    const el = document.querySelector(s); return el ? el.getBoundingClientRect().top + window.scrollY - o : 0;
  }, sel, offset);
  const hoverCta = async (on) => {
    const c = await page.evaluate(() => {
      const r = document.querySelector('#talk').getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    });
    await page.mouse.move(on ? c.x : 40, on ? c.y : 40, { steps: 18 });
  };
  const fresh = async () => {
    await page.goto(SITE, { waitUntil: 'networkidle0', timeout: 60000 });
    await page.evaluate(() => {
      const s = document.createElement('style');
      s.textContent = `#fps-hb{position:fixed;right:0;bottom:0;width:2px;height:2px;z-index:99999;animation:fpshb .033s infinite linear}
        @keyframes fpshb{0%{background:#f3efe1}50%{background:#f2eee0}100%{background:#f3efe1}}
        html{scroll-behavior:auto!important}`;
      document.head.appendChild(s);
      const d = document.createElement('div'); d.id = 'fps-hb'; document.body.appendChild(d);
    });
  };

  // A slow, curved pointer drift so the lamplight wanders across the page.
  const drift = async (pts, ms) => {
    const per = ms / pts.length;
    for (const [x, y] of pts) await page.mouse.move(x, y, { steps: Math.max(8, Math.round(per / 30)) });
  };

  // ── meet: entrance, lamplight drifting, then the CTA hover makes her smile ─
  await fresh();
  await page.goto('about:blank');
  await page.mouse.move(1400, 760);
  await scene('site_meet', len('n_meet', 3.8), async (now) => {
    await fresh();
    await drift([[1200, 620], [980, 420], [760, 360]], 1600);
    await at(now, 3.2); await hoverCta(true);
  });

  // ── channels: WhatsApp, web chat (live) and SMS/RCS (almost ready) ───────
  // Recorded alone, the page is still about:blank (meet loads it inside its scene).
  if (page.url() === 'about:blank') await fresh();
  await scene('site_channels', len('n_hub', 1.2), async (now) => {
    await page.mouse.move(1500, 300, { steps: 10 });
    await scrollTo(await topOf('#channels', 140), 1600);
    await drift([[1300, 520], [800, 600], [360, 520], [800, 430]], 6000);
  });

  await browser.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
