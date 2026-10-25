# Devpost submission checklist — AWS CDS Agentic AI Partner Hackathon

Deadline: **Oct 28, 2026, 1:00 PM PDT** · Judging Nov 6–12 · Winners Nov 19

## Registered facts
- ACE Opportunity ID: **O30226356** (status: pending approval) — paste into Devpost
- Project title: **Lucienne — Conversational Website & SEO Copilot**
- Customer: Hero Apps (hero-apps.com) · Partner: Divina Endeavors LLC
- Campaign code on the opportunity: `AWS CDS Agentic AI Hackathon -Sept. 2026`
- Tagged products: AWS End User Messaging (RCS/SMS), Amazon SES, AWS EUM Social (WhatsApp)

## What to submit
- [ ] Repo URL (public + MIT license at top of About, or private shared with judge accounts — see hackathon GitHub README for the accounts)
- [ ] Architecture diagram (mermaid in README; export a PNG for Devpost)
- [ ] Text description (~short; see pitch below)
- [ ] ~3-minute demo video (public YouTube/Vimeo, no copyrighted music)
- [ ] Deployed URL = the stack's WebDemoUrl output (+ RCS/SMS demo instructions)
- [ ] ACE opportunity ID

## 200-char pitch (already used in ACE)
Lucienne is an autonomous conversational website audit and SEO diagnostic agent.
Users text a URL via RCS to receive instant technical audits, plain-English advice,
and developer reports via Amazon SES.

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
2. (0:20) Meet Lucienne: phone in hand, text a URL via RCS/SMS. She answers in
   plain words, ranked by impact.
3. (1:00) Conversation: follow-up question ("why does that matter?"), quick replies.
4. (1:30) "Email me the full report" → SES developer briefing lands in inbox, scroll it.
5. (2:00) Architecture: diagram walk-through — EUM two-way → SNS → Lambda →
   Bedrock Converse tool loop → SES. Emphasize at-runtime CDS usage.
6. (2:40) Close: real customer (Hero Apps), ACE opportunity, what's next (WhatsApp).

## Manual AWS setup still needed (one-time)
1. Bedrock model access for Claude Sonnet 4.5 (marketplace agreement).
2. SES: dorien.vda@gmail.com verified ✓ (sandbox is fine per rules — SMTP/sandbox qualifies).
3. EUM: finish verifying +507 destination number (OTP pending since Oct 14),
   then either an RCS test agent (console → RCS → create agent → add test device)
   or a simulator/toll-free number; enable two-way → point at stack's InboundTopicArn.
4. PSI API key (free, Google Cloud console → PageSpeed Insights API) → redeploy with
   PSI_API_KEY set.
