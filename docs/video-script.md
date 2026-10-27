# Lucienne demo video — narration script + edit map

Target ~3:00. Narration = Dorien's cloned "garden" voice (ElevenLabs clone from the
Rooted video, the v5 voice). [YOU] = Dorien on camera, personal, say it your way;
the lines given are only a shape. [GARDEN] = cloned voice-over. [LUCIENNE] = her
real Polly audio from the capture (or the pulled mp3s in `video/voice-notes/`).

Footage on disk (`~/Projects/lucienne/video/`):
- `whatsapp-demo-take2.mp4` - 18.8 min real WhatsApp capture, full arc with voice notes
  (timeline: URL sent ~0:30 in; audit reply + voice note ~1:30; "yes - check the speed";
  CWV reply w/ LCP 4.5s; "why does that matter?"; email ask; address; "Done - report sent";
  final voice note at the end). Cut all waits; keep WhatsApp's "typing..." beats short.
- `webchat-take1.mp4` - 28.8s web chat: typing, inspect pose with lantern glow while she
  audits, delight SMILE flash when results land (~15-17s in; slow it down 50% for the beat).
- `email-take1.mp4` - 96s Gmail on phone: opening "Hero Apps Technical SEO & Performance
  Report", slow scroll through Critical Findings (LCP 4.5s, Impact: High) and fixes.
- `voice-notes/AUD-*.mp3` - clean audio of all five voice notes for sync/sweetening.
- `whatsapp-demo-take1.mp4` - scrap, but has a clean voice-note-arrival close-up.

## Beats

1. 0:00-0:12 [YOU on camera]
   Shape: "I build websites for small businesses in Panama. Almost none of them
   can afford an SEO agency, and honestly, most SEO reports are unreadable."

2. 0:12-0:25 [GARDEN] over a confusing dashboard screenshot, then black:
   "57 percent of small businesses have no SEO strategy at all. No wonder:
   agencies charge around three thousand dollars a month. And page two of
   Google? A fifth of one percent of clicks."

3. 0:25-0:30 Title card + [GARDEN]: "Lucienne is a text message."
   Optional 2s handheld shot of the real phone before cutting to the capture.

4. 0:30-1:05 WhatsApp beat (take2). Type hero-apps.com, send.
   [GARDEN]: "Text her any URL on WhatsApp. She reads the page, checks what
   Google sees, and answers in plain words, ranked by impact."
   Audit reply lands -> then the voice note arrives and PLAYS: let
   [LUCIENNE] speak uncut for ~8s. This is the wow beat.
   [GARDEN]: "...and she says it out loud, avec un petit accent."

5. 1:05-1:25 Speed check (take2): "yes - check the speed" -> LCP 4.5s reply.
   [GARDEN]: "Google's own data: 53 percent of mobile visits are abandoned
   when a page takes more than three seconds. Lucienne found 4.5."

6. 1:25-1:45 Web chat beat (webchat-take1): the big-screen version.
   [GARDEN]: "She lives on the web too. While she inspects, the lantern
   glows..." (inspect pose) "...and when the results land, she smiles."
   (delight flash, slow-mo). Keep her poses the visual star; no UI chrome talk.

7. 1:45-2:05 Email beat (take2 tail + email-take1): "email me the full report"
   -> "Done - full developer report sent." Cut to Gmail scroll.
   [GARDEN]: "The developer briefing arrives by email: every finding with
   impact, evidence, and the exact fix. An agency retainer runs three thousand
   a month. Lucienne is a text message."

8. 2:05-2:35 Architecture diagram (landing page "Under the hood" SVG).
   [GARDEN]: "One agent, every AWS channel. WhatsApp and SMS through End User
   Messaging, into SNS and Lambda. Amazon Bedrock runs the tool loop, DynamoDB
   remembers the conversation, Polly gives her the voice, SES sends the report."
   (If trimming, this beat compresses to 20s.)

9. 2:35-2:50 [YOU on camera]
   Shape: "Hero Apps is a real customer, registered as an ACE opportunity.
   Next up: toll-free SMS once carrier registration clears, RCS out of sandbox,
   and moving the loop to Bedrock AgentCore."

10. 2:50-3:00 Close card: portrait + "Lucienne" + lucienne.hero-apps.com +
    WhatsApp +1 857 754 4505.
    [GARDEN]: "Drop her a link. She'll bring some clarity."

## Production notes
- Garden voice: generate per-beat clips, pace the cut to the audio (same method
  as the PoquiTareas promo). No copyrighted music; light library bed only.
- WhatsApp UI was captured in English; the app on the phone is still set to
  English in case of retakes (restore: Settings > App language > Espanol).
- Voice-note playback audio is inside take2's track; if a segment is weak, lay
  the matching `voice-notes/AUD-*.mp3` underneath instead.
- Rules check: public YouTube/Vimeo, ~3 min, no copyrighted music, show the
  deployed URL and the WhatsApp number on screen.
