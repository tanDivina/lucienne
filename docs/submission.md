# Devpost submission checklist — AWS CDS Agentic AI Partner Hackathon

Deadline: **Oct 28, 2026, 1:00 PM PDT** · Judging Nov 6–12 · Winners Nov 19

## Registered facts
- ACE Opportunity ID: **O30226356** (status: pending approval) — paste into Devpost
- Project title: **Lucienne · Conversational Website & SEO Copilot** (ACE was registered with an em dash; use the middle dot on Devpost per the no-em-dash rule)
- Customer: Hero Apps (hero-apps.com) · Partner: Divina Endeavors LLC
- Campaign code on the opportunity: `AWS CDS Agentic AI Hackathon -Sept. 2026`
- Tagged products: AWS End User Messaging (RCS/SMS), Amazon SES, AWS EUM Social (WhatsApp)

## Channel status (what to claim — verified Oct 27, 2026)
- **WhatsApp: LIVE.** +1 857 754 4505 via AWS End User Messaging Social
  (WABA "Lucienne", events → SNS → Lambda). Replies in text AND Polly voice notes;
  French phrases spoken with a French voice, the rest in English. Demo this.
- **Web chat: LIVE.** Lambda Function URL, opt-in voice, mic input, pose animations.
  This is the judges' zero-setup path; lead with it in the Deployed URL field.
- **SMS/RCS: built and wired, pending carrier registration.** Two-way EUM → SNS → the
  same Lambda handler is deployed; the toll-free origination number (+1 855 341 0413)
  is still in carrier PENDING + needs toll-free registration, and RCS in sandbox only
  delivers to registered test devices. Say exactly that — do not demo SMS live.
- **Email: LIVE.** SES developer report (sandbox, allowlisted recipient — qualifies
  per the rules).

## What to submit
- [x] Repo URL: https://github.com/tanDivina/lucienne (public, MIT)
- [ ] Architecture diagram (mermaid in README; export a PNG for Devpost — the landing
      page's "Under the hood" SVG is the same diagram, screenshot-able)
- [ ] Text description (~short; see pitch below)
- [ ] ~3-minute demo video (public YouTube/Vimeo, no copyrighted music)
- [x] Deployed URL: https://3aeprrnzvxpaum6k7vq4qccvd40pcngi.lambda-url.us-east-1.on.aws/
      (landing: https://lucienne.hero-apps.com) — add the WhatsApp number for judges
      who want the messaging flow: +1 857 754 4505
- [ ] ACE opportunity ID

## 200-char pitch (ACE wording kept; Devpost description may update RCS → WhatsApp)
Lucienne is an autonomous conversational website audit and SEO diagnostic agent.
Users text a URL via WhatsApp to receive instant technical audits, plain-English
advice, and developer reports via Amazon SES.

## Why it stands out (Devpost copy, safe wording, no em dashes)
Paste into "What it does" or "What makes it different":

> **She talks, not just types.** Unlike a text-only chatbot, Lucienne answers every
> WhatsApp message with a short voice note in her own voice. Her French phrases are
> spoken by a French voice and the rest in clear English, so she sounds like a
> character, not a script.
>
> **Pay per use, own the agent.** Lucienne runs on AWS End User Messaging Social,
> Amazon Bedrock and Amazon Polly, billed per message and per reply. There is no
> monthly chatbot platform fee, and the agent, its prompts and its conversation data
> live in the business's own AWS account. The same agent also answers on web chat and
> email.

Wording rules (Oct 27 2026):
- Do NOT write "Meta's agent can't talk" or "only bot with a voice": not verified in
  Meta's docs. "Unlike a text-only chatbot" is the safe form.
- Do NOT claim "a fifth of the cost". Per reply we estimate WhatsApp ~1 cent (2 with a
  voice note) + Bedrock 1 to 3 cents; Meta Business Agent is billed per token (Meta
  estimates ~4 to 5 cents per message). Only quote a number after measuring real cost
  per reply from the AWS bill.
- Context: since Oct 1 2026 Meta charges per message for service replies inside the
  24h window too, so "WhatsApp replies are free" is no longer true.

## Stats to quote (verified Oct 25, 2026 — exact wordings + sources)
- "57% of small businesses have no SEO strategy at all." — UpCity/Pollfish 2022 survey,
  600 US/CA SMBs (via searchenginejournal.com/no-seo-strategy-2022/438639).
  Do NOT use the recycled "70%" figure — no traceable source.
- "Page two of Google gets a fifth of one percent of clicks." — Sistrix, ~80M keywords:
  position 11 = 0.17% CTR; page one takes 99.1% of organic clicks
  (sistrix.com/blog/click-probabilities-in-the-google-serps/).
- "Google's own data: 53% of mobile visits are abandoned if a page takes over
  3 seconds to load." — Google "The Need for Mobile Speed" (say "Google's own data",
  not the year — study is 2016). Use when she runs core_web_vitals on screen.
- "An SEO agency retainer averages around $3,000 a month." — Ahrefs avg $2,819/mo via
  outerboxdesign.com/articles/seo/seo-pricing-costs; Arc Intermedia ~$3,200/mo.
  Punchline: "Lucienne is a text message."

## 3-minute video beats
1. (0:00) Hook: "57% of small businesses have no SEO strategy — and no wonder:
   agencies charge three thousand dollars a month, and the reports look like this
   (confusing dashboard). Meanwhile, page two of Google gets a fifth of one percent
   of clicks." Then: "Lucienne is a text message."
2. (0:20) Meet Lucienne: phone in hand, WhatsApp +1 857 754 4505, send a URL.
   She answers in plain words, ranked by impact — then a voice note arrives and
   she SPEAKS the verdict, avec un petit accent. (The voice note is the wow beat.)
3. (1:00) Conversation: follow-up question ("why does that matter?") in WhatsApp,
   or switch to the web chat for the big-screen version with her pose animations.
4. (1:30) "Email me the full report" → SES developer briefing lands in inbox, scroll it.
5. (2:00) Architecture: diagram walk-through — EUM Social (WhatsApp) + EUM SMS/RCS
   (wired, pending carrier registration) → SNS → Lambda → Bedrock Converse tool loop
   → Polly → SES → DynamoDB. Emphasize at-runtime CDS usage.
6. (2:40) Close: real customer (Hero Apps), ACE opportunity, what's next
   (toll-free SMS once registration clears; RCS out of sandbox).

## One-time AWS setup — all DONE
1. Bedrock model access for Claude Sonnet 4.5 ✓ (Oct 24)
2. SES: dorien.vda@gmail.com verified ✓ (sandbox qualifies per rules)
3. EUM: +507 destination verified ✓ · WhatsApp WABA live ✓ (Oct 26) ·
   toll-free SMS still pending carrier + TF registration (not needed for submission)
4. PSI API key set on the Lambda ✓ (keep `PSI_API_KEY` exported on any CFN redeploy)
