#!/usr/bin/env node
// Records each animated card scene in cards.html to WORK/cards/<scene>.mp4.
// Scene length = its narration clip + padding (end card fixed).
// Usage: node record_cards.js [workdir] [scene,scene...]
const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');
const puppeteer = require('/Users/dorienvandenabbeele/Documents/antigravity/noble-pythagoras/node_modules/puppeteer-core');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const FFMPEG = '/opt/homebrew/bin/ffmpeg';
const WORK = process.argv[2] || path.join(process.env.HOME, 'Desktop', 'Lucienne_Video', 'promo_work');
const OUT = path.join(WORK, 'cards');
fs.mkdirSync(OUT, { recursive: true });
const only = process.argv[3] ? process.argv[3].split(',') : null;

const dur = (f) => {
  try { return parseFloat(execSync(`/opt/homebrew/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "${f}"`).toString()); }
  catch { return 3; }
};
const LEAD = 0.3; // narration starts this far into each card
const SCENES = [
  ['hook', 'n_hook'], ['hook2', 'n_hook2'], ['meet', 'n_meet'],
  ['arch', 'n_arch'], ['hub', 'n_hub'], ['numbers', 'n_numbers'], ['biz', 'n_biz_fallback'], ['end', 'n_close'],
];

async function recordScene(browser, scene, seconds) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1.2 });
  const url = 'file://' + path.join(__dirname, 'cards.html') + `?scene=${scene}&frames=1`;
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => window.__ready === true);
  const file = path.join(OUT, `${scene}.mp4`);
  const ff = spawn(FFMPEG, ['-y', '-framerate', '30', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-i', '-',
    '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', file]);
  ff.stderr.on('data', () => {});
  const closed = new Promise((r) => ff.on('close', r));
  // Frame-exact: seek every animation to t, then screenshot.
  const total = Math.round(seconds * 30);
  for (let i = 0; i < total; i++) {
    await page.evaluate((t) => window.seek(t), i / 30);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await closed;
  await page.close();
  console.log(`✓ ${scene}.mp4 (${seconds.toFixed(1)}s, ${total} frames)`);
}

async function main() {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--force-device-scale-factor=1', '--allow-file-access-from-files'] });
  for (const [scene, line] of SCENES) {
    if (only && !only.includes(scene)) continue;
    const seconds = scene === 'end' ? 6 : LEAD + dur(path.join(WORK, 'audio', `${line}.mp3`)) + 0.8;
    await recordScene(browser, scene, seconds);
  }
  await browser.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
