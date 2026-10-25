# Official Lucienne art — do not redraw

`lucienne.png` is the official mascot: a chic French inspector in a cream
double-breasted trench coat and dark beret, holding a glowing brass hand
lantern ("Lucienne brings light"). Generated and chosen Oct 24 2026.

Never redraw, regenerate, or substitute stock/emoji art. Every other file
here is derived from `lucienne.png`:

- `avatar.png` — 320px head + lantern crop (chat avatars)
- `pose-neutral.png` / `pose-talk.png` / `pose-blink.png` — aligned 448px
  animation frames (nano-banana edits of the official art, same character);
  the header stage flaps talk/neutral while her Polly audio plays and
  blinks when idle
- `favicon.png` / `apple-touch-icon.png` — 64 / 180 px of the same crop
- `og.jpg` — 1200×630 link-share card

Assets are served by the Lambda at `GET /assets/<name>` (see
`src/handler.py`). Reuse these same files for Devpost, the demo video,
and any promo material.
