#!/usr/bin/env node
// Records the LIVE Lucienne web chat (Lambda Function URL): voice on, audit
// hero-apps.com, a follow-up question, then the SES developer report.
// Lucienne's own Polly voice comes back base64 in each /chat response; we save
// it as WORK/audio/lu_<n>.mp3 and cue it where the reply lands.
// Writes WORK/web_raw.mp4 + WORK/web_timeline.json (marks + audio cues, seconds).
// Usage: node record_web.js [workdir]
const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');
const puppeteer = require('/Users/dorienvandenabbeele/Documents/antigravity/noble-pythagoras/node_modules/puppeteer-core');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const FFMPEG = '/opt/homebrew/bin/ffmpeg';
const APP = process.env.APP_URL || 'https://3aeprrnzvxpaum6k7vq4qccvd40pcngi.lambda-url.us-east-1.on.aws/';
const REPORT_TO = process.env.REPORT_TO || 'dorien.vda@gmail.com';
const WORK = process.argv[2] || path.join(process.env.HOME, 'Desktop', 'Lucienne_Video', 'promo_work');
const AUDIO = path.join(WORK, 'audio');
fs.mkdirSync(AUDIO, { recursive: true });
const RAW = path.join(WORK, 'web_raw.mp4');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dur = (f) => {
  try { return parseFloat(execSync(`/opt/homebrew/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "${f}"`).toString()); }
  catch { return 3; }
};

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    protocolTimeout: 420000,
    args: ['--no-sandbox', '--disable-gpu', '--window-size=1600,940', '--force-device-scale-factor=1',
      '--autoplay-policy=no-user-gesture-required', '--mute-audio'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1.2 });
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
  await page.evaluateOnNewDocument(() => { try { localStorage.setItem('lucienne-voice', 'off'); } catch (e) {} });
  await page.goto(APP, { waitUntil: 'networkidle0', timeout: 60000 });
  await sleep(600);

  // Cursor + click pulse drawn by the page so the screencast captures them.
  await page.evaluate(() => {
    const style = document.createElement('style');
    style.innerHTML = `
      #promo-cursor { position: fixed; width: 26px; height: 26px; pointer-events: none; z-index: 999999;
        transition: transform .12s ease; filter: drop-shadow(0 2px 5px rgba(0,0,0,.45)); }
      #promo-cursor.down { transform: scale(0.82); }
      .promo-click { position: fixed; width: 56px; height: 56px; border-radius: 50%; pointer-events: none; z-index: 999998;
        background: radial-gradient(circle, rgba(214,150,52,0.55) 0%, rgba(214,150,52,0) 70%);
        transform: translate(-50%,-50%) scale(.25); animation: promoClick .45s cubic-bezier(.1,.8,.3,1) forwards; }
      @keyframes promoClick { to { transform: translate(-50%,-50%) scale(1.6); opacity: 0; } }
      #fps-heartbeat { position: fixed; bottom: 0; right: 0; width: 2px; height: 2px; z-index: 999997; animation: hb .033s infinite linear; }
      @keyframes hb { 0% { background: #f3efe1 } 50% { background: #f2eee0 } 100% { background: #f3efe1 } }
    `;
    document.head.appendChild(style);
    const hb = document.createElement('div'); hb.id = 'fps-heartbeat'; document.body.appendChild(hb);
    const c = document.createElement('div');
    c.id = 'promo-cursor';
    c.innerHTML = `<svg viewBox="0 0 24 24" width="26" height="26"><path d="M5 3l14 9.2-6.6 1 3 6.3-2.7 1.3-3-6.3L5 18.6z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>`;
    c.style.left = '800px'; c.style.top = '520px';
    document.body.appendChild(c);
    window.cursorTo = (x, y) => { c.style.left = x + 'px'; c.style.top = y + 'px'; };
    window.cursorClick = (x, y) => {
      c.classList.add('down'); setTimeout(() => c.classList.remove('down'), 140);
      const p = document.createElement('div'); p.className = 'promo-click';
      p.style.left = x + 'px'; p.style.top = y + 'px'; document.body.appendChild(p);
      setTimeout(() => p.remove(), 500);
    };
  });

  const ff = spawn(FFMPEG, ['-y', '-use_wallclock_as_timestamps', '1', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-i', '-',
    '-vf', 'scale=1920:1080:flags=lanczos', '-fps_mode', 'cfr', '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', RAW]);
  ff.stderr.on('data', () => {});
  const cdp = await page.target().createCDPSession();
  let frames = 0; let t0 = null; const marks = {}; const audio = [];
  const now = () => (Date.now() - t0) / 1000;
  const mark = (name) => { marks[name] = +now().toFixed(3); console.log(`  ⏱ ${name} @ ${marks[name]}s`); };
  cdp.on('Page.screencastFrame', async ({ data, sessionId }) => {
    try { if (t0 === null) t0 = Date.now(); frames++; ff.stdin.write(Buffer.from(data, 'base64')); await cdp.send('Page.screencastFrameAck', { sessionId }); } catch {}
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, everyNthFrame: 1 });
  while (t0 === null) await sleep(20);

  // Narrator pacing.
  const played = [];
  const speak = (name) => {
    const file = path.join(AUDIO, `${name}.mp3`);
    audio.push({ name, file, t: +now().toFixed(3) });
    played.push({ end: now() + dur(file) });
    console.log(`  🔊 ${name} @ ${now().toFixed(2)}s`);
  };
  const settle = async (extra = 0.6) => {
    const end = Math.max(0, ...played.map((p) => p.end));
    const wait = end + extra - now();
    if (wait > 0) await sleep(wait * 1000);
  };

  // Lucienne's voice: capture each /chat reply's audio as it arrives.
  let replyN = 0;
  page.on('response', async (res) => {
    if (!res.url().endsWith('/chat') || res.request().method() !== 'POST') return;
    try {
      const data = await res.json();
      replyN++;
      const t = +now().toFixed(3);
      if (data.audio) {
        const file = path.join(AUDIO, `lu_${replyN}.mp3`);
        fs.writeFileSync(file, Buffer.from(data.audio, 'base64'));
        audio.push({ name: `lu_${replyN}`, file, t, lucienne: true });
        played.push({ end: t + dur(file) });
        console.log(`  🗣  lu_${replyN} @ ${t}s (${dur(file).toFixed(1)}s): ${(data.reply || '').slice(0, 90)}…`);
      } else {
        console.log(`  (reply ${replyN} without audio): ${(data.reply || data.error || '').slice(0, 120)}`);
      }
    } catch (e) { console.log('response parse failed', e.message); }
  });

  let cx = 800, cy = 520;
  async function moveTo(x, y, ms = 550) {
    const fx = cx, fy = cy, steps = Math.max(10, Math.round(ms / 33));
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      cx = fx + (x - fx) * e; cy = fy + (y - fy) * e;
      await page.evaluate((a, b) => window.cursorTo(a, b), cx, cy);
      await sleep(ms / steps);
    }
  }
  async function clickSel(sel, ms = 550) {
    const c = await page.evaluate((s) => {
      const el = typeof s === 'string' && s.startsWith('text=')
        ? [...document.querySelectorAll('button')].find((b) => b.textContent.trim() === s.slice(5))
        : document.querySelector(s);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    }, sel);
    if (!c) throw new Error(`not found: ${sel}`);
    await moveTo(c.x, c.y, ms); await sleep(140);
    await page.evaluate((a, b) => window.cursorClick(a, b), cx, cy);
    await page.mouse.click(cx, cy);
    await sleep(260);
  }
  async function typeAndSend(text) {
    await clickSel('#inp', 450);
    await page.keyboard.type(text, { delay: 28 });
    await sleep(350);
    await clickSel('#send', 400);
  }
  const waitReply = async (n, timeout = 90000) => {
    await page.waitForFunction((k) => {
      const msgs = document.querySelectorAll('.msg:not(.me)');
      return msgs.length >= k + 1 && !document.querySelector('.msg.thinking');
    }, { timeout, polling: 100 }, n);
    // The page doesn't re-scroll when the reply text fills in; bring its top into view.
    await page.evaluate(() => {
      const msgs = document.querySelectorAll('.msg:not(.me)');
      msgs[msgs.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  // ── Scene: voice on, audit hero-apps.com ──────────────────────────────────
  mark('web'); console.log('Scene: web chat');
  speak('n_web');
  await sleep(900);
  await clickSel('#voice', 700);
  await sleep(500);
  await clickSel('text=Audit hero-apps.com', 700);
  mark('think1_start');
  await waitReply(1);
  mark('think1_end');
  await sleep(300);
  await settle(1.2);

  // ── Scene: follow-up question ─────────────────────────────────────────────
  mark('follow'); console.log('Scene: follow-up');
  speak('n_follow');
  await sleep(600);
  await typeAndSend('Why does a slow first byte matter to my visitors?');
  mark('think2_start');
  await waitReply(2);
  mark('think2_end');
  await sleep(300);
  await settle(1.2);

  // ── Scene: SES developer report ───────────────────────────────────────────
  mark('email'); console.log('Scene: email report');
  speak('n_email');
  await sleep(600);
  await typeAndSend(`Yes please, email the full developer report to ${REPORT_TO}`);
  mark('think3_start');
  await waitReply(3, 200000);
  mark('think3_end');
  await sleep(300);
  await settle(1.5);
  mark('end');

  await cdp.send('Page.stopScreencast');
  await sleep(300);
  const transcript = await page.evaluate(() => [...document.querySelectorAll('.msg')].map((m) => m.innerText));
  await browser.close();
  await new Promise((r) => { ff.stdin.end(); ff.on('close', r); });
  fs.writeFileSync(path.join(WORK, 'web_timeline.json'), JSON.stringify({ fps: 30, frames, seconds: marks.end, marks, audio, transcript }, null, 2));
  console.log(`\n✅ ${RAW} (${frames} frames, ${marks.end}s)`);
}
main().catch((e) => { console.error(e); process.exit(1); });
