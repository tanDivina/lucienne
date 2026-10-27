#!/usr/bin/env node
// Composes the final 1920x1080 Lucienne video from:
//   cards/<scene>.mp4 (record_cards.js) + narration in audio/
//   web_raw.mp4 + web_timeline.json (record_web.js), thinking waits cut short
//   optional phone clips: whatsapp.mov (WhatsApp audit + voice note), inbox.mov (SES email)
// Each segment is rendered to seg/NN.mp4 with its own audio, then concatenated.
// Usage: node compose.js [workdir] [out.mp4]
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const FFMPEG = '/opt/homebrew/bin/ffmpeg';
const FFPROBE = '/opt/homebrew/bin/ffprobe';
const WORK = process.argv[2] || path.join(process.env.HOME, 'Desktop', 'Lucienne_Video', 'promo_work');
const OUT = process.argv[3] || path.join(path.dirname(WORK), 'lucienne_demo.mp4');
const SEG = path.join(WORK, 'seg');
fs.mkdirSync(SEG, { recursive: true });
const A = (n) => path.join(WORK, 'audio', `${n}.mp3`);
const FONT = '/System/Library/Fonts/Supplemental/Georgia Italic.ttf';
const PAPER = '0xf3efe1';
const LEAD = 0.3;
// Where each of Lucienne's voice notes stops (sentence breaks, from whisper timings).
const VOICE_CAP = { lu_1: 8.6, lu_3: 14.5 };

const dur = (f) => parseFloat(execFileSync(FFPROBE, ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString());
const hasAudio = (f) => execFileSync(FFPROBE, ['-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', f]).toString().trim() !== '';
const ff = (args) => execFileSync(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-y', ...args], { stdio: ['ignore', 'inherit', 'inherit'] });
const V_OUT = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30'];
const A_OUT = ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2'];

// Mixes a list of {file, t, vol} cues into the segment audio (silence-padded to `len`).
function mixArgs(cues, firstInput, len) {
  const parts = cues.map((c, i) => {
    const ms = Math.max(0, Math.round(c.t * 1000));
    const cap = c.cap ? `,atrim=0:${c.cap.toFixed(3)},afade=t=out:st=${(c.cap - 0.35).toFixed(3)}:d=0.35` : '';
    return `[${firstInput + i}:a]aformat=sample_rates=48000:channel_layouts=stereo${cap},volume=${c.vol ?? 1},adelay=${ms}|${ms}[a${i}]`;
  });
  const labels = cues.map((_, i) => `[a${i}]`).join('');
  const mix = cues.length
    ? `${labels}amix=inputs=${cues.length}:normalize=0:dropout_transition=0,apad,atrim=0:${len.toFixed(3)}[aout]`
    : `anullsrc=r=48000:cl=stereo,atrim=0:${len.toFixed(3)}[aout]`;
  return [...parts, mix].join(';');
}

let n = 0;
const segs = [];
const nextSeg = () => path.join(SEG, `${String(++n).padStart(2, '0')}.mp4`);

// A card scene: video as recorded, narration at LEAD.
function card(scene, line) {
  const v = path.join(WORK, 'cards', `${scene}.mp4`);
  if (!fs.existsSync(v)) { console.log(`skip card ${scene} (missing)`); return; }
  const len = dur(v);
  const out = nextSeg();
  ff(['-i', v, '-i', A(line), '-filter_complex', mixArgs([{ t: LEAD }], 1, len), '-map', '0:v', '-map', '[aout]', ...V_OUT, ...A_OUT, '-t', len.toFixed(3), out]);
  segs.push(out); console.log(`✓ ${path.basename(out)} card ${scene} ${len.toFixed(1)}s`);
}

// A phone screen recording (portrait or landscape), centred on paper, with
// narration over its opening and the clip's own sound (her voice note) kept.
function phone(file, line, { trimStart = 0, maxLen = 40 } = {}) {
  if (!fs.existsSync(file)) { console.log(`skip ${path.basename(file)} (not recorded yet)`); return; }
  const len = Math.min(maxLen, dur(file) - trimStart);
  const out = nextSeg();
  const cues = line ? [{ t: LEAD }] : [];
  const inputs = ['-ss', String(trimStart), '-t', len.toFixed(3), '-i', file, ...(line ? ['-i', A(line)] : [])];
  let fc = `[0:v]scale=-2:1000:flags=lanczos,format=yuv420p,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=${PAPER},setsar=1[v];`;
  if (hasAudio(file)) {
    fc += `[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0[ph];`;
    fc += (cues.length ? mixArgs(cues, 1, len).replace('[aout]', '[nar]') : `anullsrc=r=48000:cl=stereo,atrim=0:${len.toFixed(3)}[nar]`) + `;[nar][ph]amix=inputs=2:normalize=0:dropout_transition=0,atrim=0:${len.toFixed(3)}[aout]`;
  } else {
    fc += mixArgs(cues, 1, len);
  }
  ff([...inputs, '-filter_complex', fc, '-map', '[v]', '-map', '[aout]', ...V_OUT, ...A_OUT, out]);
  segs.push(out); console.log(`✓ ${path.basename(out)} phone ${path.basename(file)} ${len.toFixed(1)}s`);
}

// The web chat: keep everything except the middle of each thinking wait.
function web() {
  const raw = path.join(WORK, 'web_raw.mp4');
  if (!fs.existsSync(raw)) { console.log('skip web (missing)'); return; }
  const tl = JSON.parse(fs.readFileSync(path.join(WORK, 'web_timeline.json')));
  const m = tl.marks; const T = dur(raw);
  const HEAD = 1.4, TAIL = 0.9; // seconds of "thinking" kept either side of each cut
  const cuts = [];
  for (const k of [1, 2, 3]) {
    const s = m[`think${k}_start`], e = m[`think${k}_end`];
    if (s != null && e != null && e - s > HEAD + TAIL + 1) cuts.push({ a: s + HEAD, b: e - TAIL, real: e - s, wait: true });
  }
  // Long voice notes end at a sentence break; the video skips the rest of her speech.
  for (const c of tl.audio.filter((x) => x.lucienne && VOICE_CAP[x.name])) {
    const cap = VOICE_CAP[c.name], full = dur(c.file);
    if (cap < full - 0.5 && c.t + cap + 0.6 < T - 1) cuts.push({ a: c.t + cap + 0.6, b: Math.min(T - 1, c.t + full) });
  }
  cuts.sort((x, y) => x.a - y.a);
  const keeps = []; let t = 0;
  for (const c of cuts) { keeps.push([t, c.a]); t = c.b; }
  keeps.push([t, T]);
  const mapT = (x) => { let off = 0; for (const c of cuts) { if (x >= c.b) off += c.b - c.a; else if (x > c.a) return c.a - off; } return x - off; };
  const len = keeps.reduce((s, [a, b]) => s + (b - a), 0);

  let fc = keeps.map(([a, b], i) => `[0:v]trim=${a.toFixed(3)}:${b.toFixed(3)},setpts=PTS-STARTPTS[k${i}]`).join(';');
  fc += ';' + keeps.map((_, i) => `[k${i}]`).join('') + `concat=n=${keeps.length}:v=1:a=0[vc]`;
  // Honest label wherever a wait was shortened (PNG via ImageMagick; this ffmpeg has no drawtext).
  let vlast = 'vc';
  const labels = [];
  cuts.filter((c) => c.wait).forEach((c, i) => {
    const at = mapT(c.a);
    const secs = Math.round(c.real);
    const text = secs >= 60 ? `${Math.floor(secs / 60)} min ${secs % 60} s` : `${secs} s`;
    const png = path.join(WORK, `label_${i}.png`);
    execFileSync('/opt/homebrew/bin/magick', ['-background', '#faf7ec', '-fill', '#8a6d1f', '-font', FONT, '-pointsize', '30',
      `label:real wait ${text}, shortened`, '-bordercolor', '#faf7ec', '-border', '22x14', png]);
    labels.push({ png, at });
  });
  labels.forEach((l, i) => {
    fc += `;[${vlast}][L${i}]overlay=x=W-w-60:y=60:enable='between(t,${(l.at - 0.6).toFixed(2)},${(l.at + 1.8).toFixed(2)})'[vd${i}]`;
    vlast = `vd${i}`;
  });
  const cues = tl.audio.map((c) => ({ file: c.file, t: mapT(c.t), vol: c.lucienne ? 1.4 : 1, cap: c.lucienne ? VOICE_CAP[c.name] : undefined }));
  const inputs = ['-i', raw, ...cues.flatMap((c) => ['-i', c.file]), ...labels.flatMap((l) => ['-i', l.png])];
  labels.forEach((_, i) => { fc = `[${1 + cues.length + i}:v]format=rgba[L${i}];` + fc; });
  fc += ';' + mixArgs(cues, 1, len);
  const out = nextSeg();
  ff([...inputs, '-filter_complex', fc, '-map', `[${vlast}]`, '-map', '[aout]', ...V_OUT, ...A_OUT, out]);
  segs.push(out); console.log(`✓ ${path.basename(out)} web ${len.toFixed(1)}s (raw ${T.toFixed(1)}s, ${cuts.length} waits shortened)`);
}

fs.readdirSync(SEG).forEach((f) => fs.unlinkSync(path.join(SEG, f)));
card('hook', 'n_hook');
card('hook2', 'n_hook2');
card('meet', 'n_meet');
phone(path.join(WORK, 'whatsapp.mov'), 'n_whatsapp', { maxLen: 45 });
web();
phone(path.join(WORK, 'inbox.mov'), null, { maxLen: 12 });
card('arch', 'n_arch');
card('hub', 'n_hub');
card('biz', 'n_biz');
card('end', 'n_outro');

const list = path.join(SEG, 'list.txt');
fs.writeFileSync(list, segs.map((s) => `file '${s}'`).join('\n'));
ff(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', OUT]);
console.log(`\n✅ ${OUT} (${dur(OUT).toFixed(1)}s, ${segs.length} segments)`);
