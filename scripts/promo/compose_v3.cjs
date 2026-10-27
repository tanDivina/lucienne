#!/usr/bin/env node
// Lucienne demo v3 (1920x1080), built on the Don Tuco lessons:
//   readable phone (keyboard cropped), side cards naming the real tool and the
//   real on-phone reply time, labelled speed-ups, a ducked café music bed,
//   measured cost, live-site scenes, and slots for Dorien on camera.
// Inputs (v3_work): cards/*.mp4 (record_cards.js), site/*.mp4 (record_site.cjs),
//   whatsapp_take.mkv + voice/vn1.mp3, vn2.mp3 (her voice notes pulled off the
//   phone: scrcpy can't capture WhatsApp playback), lucienne_music.mp3,
//   audio/ -> video/merge/audio (garden-voice narration),
//   ~/Desktop/Lucienne_Video/promo_work/web_raw.mp4 + web_timeline.json (web chat),
//   ~/Projects/lucienne/video/email-take1.mp4 (Gmail, the styled report),
//   ../personal/l1_open, l2_story (Dorien on camera; slates until filmed).
// Usage: node compose_v3.cjs [out.mp4]
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const FFMPEG = '/opt/homebrew/bin/ffmpeg';
const FFPROBE = '/opt/homebrew/bin/ffprobe';
const MAGICK = '/opt/homebrew/bin/magick';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const ROOT = path.join(process.env.HOME, 'Desktop', 'Lucienne_Video');
const WORK = path.join(ROOT, 'v3_work');
const PERSONAL = path.join(ROOT, 'personal');
const OUT = process.argv[2] || path.join(ROOT, 'lucienne_demo_v3.mp4');
const SEG = path.join(WORK, 'seg');
fs.mkdirSync(SEG, { recursive: true });
const LEAD = 0.3;
const PAPER = '#f3efe1', INK = '#221c13', AMBER = '#8a6d1f';
const MUSIC = path.join(WORK, 'lucienne_music.mp3');
const MUSIC_DB = -20;

const A = (n) => path.join(WORK, 'audio', `${n}.mp3`);
const dur = (f) => parseFloat(execFileSync(FFPROBE, ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString());
const hasAudio = (f) => execFileSync(FFPROBE, ['-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', f]).toString().trim() !== '';
const ff = (args) => execFileSync(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-y', ...args], { stdio: ['ignore', 'inherit', 'inherit'] });
const V_OUT = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30'];
const A_OUT = ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2'];
const find = (base) => ['.mov', '.mp4', '.mkv', '.MOV', '.MP4'].map((e) => path.join(PERSONAL, base + e)).find(fs.existsSync);

// cues: [{file, t, vol?, cap?}] -> mixed [aout] of length len
function mix(cues, firstInput, len) {
  if (!cues.length) return `anullsrc=r=48000:cl=stereo,atrim=0:${len.toFixed(3)}[aout]`;
  const parts = cues.map((c, i) => {
    const ms = Math.max(0, Math.round(c.t * 1000));
    const cap = c.cap ? `,atrim=0:${c.cap.toFixed(3)},afade=t=out:st=${(c.cap - 0.3).toFixed(3)}:d=0.3` : '';
    return `[${firstInput + i}:a]aformat=sample_rates=48000:channel_layouts=stereo${cap},volume=${c.vol ?? 1},adelay=${ms}|${ms}[a${i}]`;
  });
  return [...parts, `${cues.map((_, i) => `[a${i}]`).join('')}amix=inputs=${cues.length}:normalize=0:dropout_transition=0,apad,atrim=0:${len.toFixed(3)}[aout]`].join(';');
}

// Paper card rendered by headless Chrome (transparent background).
function card(file, lines, width = 500) {
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const body = lines.map(([text, size, color, font]) =>
    `<div style="font:${size}px/1.25 ${font === 'mono' ? 'Menlo, monospace' : font === 'italic' ? 'italic Georgia, serif' : 'Georgia, serif'};color:${color};margin:0 0 ${Math.round(size * 0.35)}px">${esc(text)}</div>`).join('');
  const html = file.replace(/\.png$/, '.html');
  fs.writeFileSync(html, `<!doctype html><html><body style="margin:0;background:transparent">
<div style="display:inline-block;box-sizing:border-box;width:${width}px;background:#faf7ec;border:2px solid #e4dcc6;border-radius:18px;padding:24px 28px 14px;box-shadow:0 10px 26px rgba(80,60,20,.12)">${body}</div></body></html>`);
  execFileSync(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
    '--default-background-color=00000000', `--window-size=${width + 30},440`, `--screenshot=${file}`, 'file://' + html], { stdio: 'ignore' });
  execFileSync(MAGICK, [file, '-trim', '+repage', file]);
  return file;
}

let n = 0;
const segs = [];
const next = () => path.join(SEG, `${String(++n).padStart(2, '0')}.mp4`);

// A recorded clip (card or site scene) with narration; held on its last frame if the voice runs longer.
function clip(file, line, { lead = LEAD, tail = 0.6 } = {}) {
  const v = path.join(WORK, file);
  const need = line ? lead + dur(A(line)) + tail : 0;
  const len = Math.max(dur(v), need); const out = next();
  const cs = line ? [{ file: A(line), t: lead }] : [];
  ff(['-i', v, ...cs.flatMap((c) => ['-i', c.file]), '-filter_complex',
    `[0:v]tpad=stop_mode=clone:stop_duration=${Math.max(0, len - dur(v) + 0.1).toFixed(3)},trim=0:${len.toFixed(3)},setpts=PTS-STARTPTS[v];` + mix(cs, 1, len),
    '-map', '[v]', '-map', '[aout]', ...V_OUT, ...A_OUT, '-t', len.toFixed(3), out]);
  segs.push(out); console.log(`✓ ${path.basename(out)} ${file} ${len.toFixed(1)}s`);
}

function slate(label, script, seconds) {
  const png = path.join(WORK, `slate_${n + 1}.png`);
  execFileSync(MAGICK, ['-size', '1920x1080', `xc:${PAPER}`,
    '-font', '/System/Library/Fonts/Supplemental/Georgia.ttf', '-fill', AMBER, '-pointsize', '34', '-gravity', 'north', '-annotate', '+0+170', label.toUpperCase(),
    '(', '-size', '1400x', '-background', 'none', '-font', '/System/Library/Fonts/Supplemental/Georgia Italic.ttf', '-fill', INK, '-pointsize', '50', '-gravity', 'center', `caption:${script}`, ')',
    '-gravity', 'center', '-geometry', '+0+40', '-composite', png]);
  const out = next();
  ff(['-loop', '1', '-t', String(seconds), '-i', png, '-filter_complex', `[0:v]scale=1920:1080,format=yuv420p[v];` + mix([], 1, seconds),
    '-map', '[v]', '-map', '[aout]', ...V_OUT, ...A_OUT, '-t', String(seconds), out]);
  segs.push(out); console.log(`… ${path.basename(out)} SLATE ${label} ${seconds}s`);
}

function personal(base, label, script, seconds) {
  const f = find(base);
  if (!f) return slate(label, script, seconds);
  const len = dur(f); const out = next();
  const v = `[0:v]scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=${PAPER},setsar=1,format=yuv420p[v]`;
  const a = hasAudio(f) ? `[0:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5[aout]` : `anullsrc=r=48000:cl=stereo,atrim=0:${len}[aout]`;
  ff(['-i', f, '-filter_complex', `${v};${a}`, '-map', '[v]', '-map', '[aout]', ...V_OUT, ...A_OUT, '-t', len.toFixed(3), out]);
  segs.push(out); console.log(`✓ ${path.basename(out)} personal ${path.basename(f)} ${len.toFixed(1)}s`);
}

// Generic piece editor: pieces [{a,b,k}] of one source, centred on paper,
// side cards [{png, from, to, side}] and audio cues on the output timeline.
function edit({ src, crop, height, pieces, cards, cues, tailHold = 0 }) {
  let t = 0;
  for (const p of pieces) { p.at = t; t += (p.b - p.a) / p.k; }
  const len = t + tailHold;
  const cropF = crop ? `crop=${crop.w}:${crop.h}:${crop.x}:${crop.y},` : '';
  let fc = `[0:v]fps=30,${cropF}scale=-2:${height}:flags=lanczos,setsar=1,split=${pieces.length}${pieces.map((_, i) => `[p${i}]`).join('')};`;
  fc += pieces.map((p, i) => `[p${i}]trim=${p.a.toFixed(3)}:${p.b.toFixed(3)},setpts=(PTS-STARTPTS)/${p.k.toFixed(4)}[q${i}]`).join(';');
  fc += ';' + pieces.map((_, i) => `[q${i}]`).join('') + `concat=n=${pieces.length}:v=1:a=0,fps=30,tpad=stop_mode=clone:stop_duration=${(tailHold + 0.1).toFixed(2)}[ph];`;
  fc += `color=c=${PAPER}:s=1920x1080:r=30:d=${len.toFixed(3)}[bg];[bg][ph]overlay=x=(W-w)/2:y=(H-h)/2:shortest=1[v0]`;
  const imgBase = 1 + cues.length;
  let last = 'v0';
  cards.forEach((c, k) => {
    const x = c.side === 'left' ? '80' : 'W-w-80';
    fc += `;[${last}][${imgBase + k}:v]overlay=x=${x}:y=(H-h)/2:enable='between(t,${c.from.toFixed(2)},${c.to.toFixed(2)})'[c${k}]`;
    last = `c${k}`;
  });
  fc += ';' + mix(cues, 1, len);
  const out = next();
  ff(['-i', src, ...cues.flatMap((c) => ['-i', c.file]), ...cards.flatMap((c) => ['-i', c.png]),
    '-filter_complex', fc, '-map', `[${last}]`, '-map', '[aout]', ...V_OUT, ...A_OUT, '-t', len.toFixed(3), out]);
  segs.push(out); console.log(`✓ ${path.basename(out)} ${path.basename(src)} ${len.toFixed(1)}s`);
  return pieces;
}

// ── WhatsApp: real take on panacacao.com (phone clock = video clock) ─────────
function whatsapp() {
  const src = path.join(WORK, 'whatsapp_take.mkv');
  const W = 2.5; // seconds a wait is shown
  // sent / reply-on-phone / voice play start, from scene detection on the take
  const s1 = 14.3, r1 = 27.8, v1 = 35.1, s2 = 72.7, r2 = 95.2, v2 = 142.3;
  const VN1 = 13.6, VN2 = 11.2; // voice notes end at a sentence break
  const pieces = [
    { a: s1 - 3.0, b: s1, k: 1 },                    // 0 typing panacacao.com
    { a: s1, b: r1, k: (r1 - s1) / W },              // 1 wait (inspect_page)
    { a: r1, b: r1 + 6.0, k: 1 },                    // 2 read the audit
    { a: v1 - 1.0, b: v1 + VN1 + 0.6, k: 1 },        // 3 voice note 1 plays
    { a: s2 - 2.4, b: s2, k: 1 },                    // 4 typing "check the speed"
    { a: s2, b: r2, k: (r2 - s2) / W },              // 5 wait (core_web_vitals)
    { a: r2, b: r2 + 8.5, k: 1 },                    // 6 read the speed reply
    { a: v2 - 1.0, b: Math.min(v2 + VN2 + 0.6, dur(src) - 0.05), k: 1 }, // 7 voice note 2
  ];
  let t = 0; for (const p of pieces) { p.at = t; t += (p.b - p.a) / p.k; }
  const P = (i) => pieces[i].at;
  const end = (i) => pieces[i].at + (pieces[i].b - pieces[i].a) / pieces[i].k;
  const tailHold = Math.max(0, (P(7) + 1.0 + VN2 + 0.4) - end(7));

  const badge = card(path.join(WORK, 'wa_badge.png'), [
    ['LIVE AGENT · REAL PHONE', 20, AMBER], ['Recorded Oct 27, 2026', 34, INK],
    ['WhatsApp through AWS End User Messaging Social. Nothing staged, nothing edited inside the chat.', 23, '#6b5f4c', 'italic']]);
  const stamp = (name, real, tool, detail, faster = true) => card(path.join(WORK, `wa_${name}.png`), [
    [real, 44, INK], [tool, 28, AMBER, 'mono'], [detail, 26, '#4b402f'],
    [faster ? 'real reply time on the phone; the wait is shown faster' : 'her own voice, sent as a WhatsApp audio message', 18, '#8d816c', 'italic']]);
  const c1 = stamp('s1', `replied in ${(r1 - s1).toFixed(1)} s`, 'inspect_page', 'fetched the live page: status, speed, headings, alt text, schema, social cards');
  const c2 = stamp('s2', 'voice note', 'Amazon Polly', 'French phrases in a French voice, the rest in English', false);
  const c3 = stamp('s3', `replied in ${(r2 - s2).toFixed(1)} s`, 'core_web_vitals', 'PageSpeed Insights, mobile: LCP 5.9 s, CLS 0, TBT 0 ms');
  const cards = [
    { png: badge, from: 0, to: t + tailHold, side: 'left' },
    { png: c1, from: P(1), to: end(2), side: 'right' },
    { png: c2, from: P(3), to: end(3), side: 'right' },
    { png: c3, from: P(5), to: end(6), side: 'right' },
    { png: c2, from: P(7), to: t + tailHold, side: 'right' },
  ];
  const cues = [
    { file: A('n_wa1'), t: 0.4 },
    { file: A('n_voice'), t: Math.max(end(2) - 2.4, 9.6) },
    { file: path.join(WORK, 'voice', 'vn1.mp3'), t: P(3) + 1.0, cap: VN1, vol: 1.25 },
    { file: A('n_speed'), t: P(4) + 0.2 },
    { file: path.join(WORK, 'voice', 'vn2.mp3'), t: P(7) + 1.0, cap: VN2, vol: 1.25 },
  ];
  edit({ src, crop: { w: 1080, h: 1560, x: 0, y: 0 }, height: 1000, pieces, cards, cues, tailHold });
}

// ── Web chat: Hero Apps, the lantern glows while she inspects, then she smiles ──
function web() {
  const raw = path.join(ROOT, 'promo_work', 'web_raw.mp4');
  const tl = JSON.parse(fs.readFileSync(path.join(ROOT, 'promo_work', 'web_timeline.json')));
  const m = tl.marks;
  const real = m.think1_end - m.think1_start;
  const pieces = [
    { a: 0.6, b: m.think1_start + 1.6, k: 1 },
    { a: m.think1_start + 1.6, b: m.think1_end - 0.4, k: (real - 2.0) / 2.4 },
    { a: m.think1_end - 0.4, b: m.think1_end + 4.2, k: 1 },
  ];
  let t = 0; for (const p of pieces) { p.at = t; t += (p.b - p.a) / p.k; }
  const note = card(path.join(WORK, 'web_note.png'), [
    ['Web chat · Lambda Function URL', 22, AMBER], ['audit of hero-apps.com', 30, INK],
    [`real reply time ${real.toFixed(1)} s; the wait is shown faster`, 18, '#8d816c', 'italic']], 440);
  // full-frame recording: the note sits bottom-right over the empty margin
  const out = next();
  const need = Math.max(t, LEAD + dur(A('n_web')) + 0.4);
  let fc = `[0:v]split=3[p0][p1][p2];` + pieces.map((p, i) => `[p${i}]trim=${p.a.toFixed(3)}:${p.b.toFixed(3)},setpts=(PTS-STARTPTS)/${p.k.toFixed(4)}[q${i}]`).join(';');
  fc += `;[q0][q1][q2]concat=n=3:v=1:a=0,fps=30,tpad=stop_mode=clone:stop_duration=${(need - t + 0.1).toFixed(2)}[w];`;
  fc += `[w][2:v]overlay=x=W-w-60:y=H-h-120:enable='between(t,${pieces[1].at.toFixed(2)},${need.toFixed(2)})'[v];`;
  fc += mix([{ file: A('n_web'), t: LEAD }], 1, need);
  ff(['-i', raw, '-i', A('n_web'), '-i', note, '-filter_complex', fc, '-map', '[v]', '-map', '[aout]', ...V_OUT, ...A_OUT, '-t', need.toFixed(3), out]);
  segs.push(out); console.log(`✓ ${path.basename(out)} web ${need.toFixed(1)}s`);
}

// ── Email: the styled report in Gmail, cropped to the message body ───────────
function email() {
  const src = path.join(process.env.HOME, 'Projects', 'lucienne', 'video', 'email-take1.mp4');
  const pieces = [{ a: 12.4, b: 34.0, k: 2.0 }];  // opens at 12.4 s with her header card
  const note = card(path.join(WORK, 'email_note.png'), [
    ['Amazon SES', 22, AMBER], ['The developer briefing', 32, INK],
    ['every finding with impact, evidence and the exact fix', 24, '#4b402f'], ['scroll shown 2× faster', 18, '#8d816c', 'italic']], 460);
  const len = Math.max(11.0, LEAD + dur(A('n_email')) + 0.6);
  edit({ src, crop: { w: 1080, h: 1060, x: 0, y: 880 }, height: 1000, pieces,  // below the sender line, above the reply buttons
    cards: [{ png: note, from: 0, to: len, side: 'right' }], cues: [{ file: A('n_email'), t: LEAD }], tailHold: Math.max(0, len - 11.0) });
}

fs.readdirSync(SEG).forEach((f) => fs.unlinkSync(path.join(SEG, f)));
personal('l1_open', 'Your clip L1: opener, about 10 s',
  "I build websites for small businesses in Panama. Almost none of them can afford an SEO agency, and the reports they do get are unreadable.", 10);
clip('cards/hook.mp4', 'n_hook');
clip('cards/hook2.mp4', 'n_hook2');
clip('site/site_meet.mp4', 'n_meet', { lead: 1.6 });
whatsapp();
web();
email();
clip('site/site_channels.mp4', 'n_hub');
clip('cards/arch.mp4', 'n_arch');
clip('cards/numbers.mp4', 'n_numbers');
// Dorien's partner story if filmed, else the partner card with the garden-voice line.
if (find('l2_story')) personal('l2_story', '', '', 0);
else clip('cards/biz.mp4', 'n_biz_fallback');
clip('cards/end.mp4', 'n_close', { tail: 1.6 });

// Concatenate, then the café bed: looped, ducked under every voice, faded out.
const list = path.join(SEG, 'list.txt');
fs.writeFileSync(list, segs.map((s) => `file '${s}'`).join('\n'));
const joined = path.join(WORK, 'joined.mp4');
ff(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', joined]);
const T = dur(joined);
const md = dur(MUSIC);
const loops = Math.ceil(T / (md - 3)) + 1;
let mfc = '';
for (let i = 0; i < loops; i++) mfc += `[${1 + i}:a]aformat=sample_rates=48000:channel_layouts=stereo[m${i}];`;
let last = 'm0';
for (let i = 1; i < loops; i++) { mfc += `[${last}][m${i}]acrossfade=d=3[mx${i}];`; last = `mx${i}`; }
mfc += `[${last}]atrim=0:${T.toFixed(3)},volume=${MUSIC_DB}dB,afade=t=in:d=1.5,afade=t=out:st=${(T - 3).toFixed(3)}:d=3[bed];`;
mfc += `[0:a]asplit=2[voice][key];[bed][key]sidechaincompress=threshold=0.02:ratio=8:attack=40:release=600[ducked];`;
mfc += `[voice][ducked]amix=inputs=2:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=11[aout]`;
ff(['-i', joined, ...Array.from({ length: loops }, () => ['-i', MUSIC]).flat(), '-filter_complex', mfc,
  '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', ...A_OUT, '-movflags', '+faststart', OUT]);
console.log(`\n✅ ${OUT} (${dur(OUT).toFixed(1)}s, ${segs.length} segments)`);
