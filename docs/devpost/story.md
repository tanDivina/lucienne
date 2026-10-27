## Inspiration
57% of small businesses have no SEO strategy at all (UpCity survey of 600 US and Canadian SMBs). That's no surprise: an SEO agency retainer averages around $3,000 a month, and the free tools hand owners a dashboard of red numbers nobody explains. Meanwhile page two of Google gets a fifth of one percent of clicks (Sistrix, 80M keywords).

We build websites for small tourism and hospitality businesses in Panama. Our clients don't open dashboards. They live in WhatsApp. So we asked: what if a website audit was just a message?

## What it does
**Lucienne is a text message.** Send her a website address on WhatsApp and she inspects it like a meticulous senior engineer, then explains what she found in plain words, ranked by impact and sized for a chat bubble.

- **Inspects for real.** An agent on Amazon Bedrock decides which checks the conversation needs and runs them: page inspection (status, redirects, TTFB, page weight, title, meta, canonical, robots, headings, image alts, Open Graph, JSON-LD, noindex), robots.txt and sitemap health, and Core Web Vitals from Google PageSpeed Insights (lab plus real-user data).
- **Talks, not just types.** Unlike a text-only chatbot, Lucienne follows each WhatsApp reply with a short voice note in her own voice. Her French phrases are spoken by a French voice and the rest in clear English, so she sounds like a character, not a script.
- **Remembers the conversation.** Ask "why does that matter?" or "how do I fix it?" and she answers in context.
- **Delivers the deep report.** Ask for it and a full HTML developer briefing lands in the inbox through Amazon SES, ready to forward to whoever builds the site.
- **Same agent, every channel.** WhatsApp (live), a web chat with voice and mic input (live, zero setup for judges), email (live) and SMS/RCS through the same handler (wired, pending toll-free carrier registration).

## How we built it
- **AWS End User Messaging Social** receives WhatsApp messages and delivers them through SNS to an **AWS Lambda** (Python, standard library only).
- The Lambda runs a **Bedrock Converse** tool-use loop (Claude Sonnet 4.5) with four tools: `inspect_page`, `check_robots_sitemap`, `core_web_vitals` and `email_report`.
- Replies go back with `SendWhatsAppMessage`. **Amazon Polly** renders the voice note, which is uploaded with `PostWhatsAppMessageMedia` and sent as audio.
- **DynamoDB** keeps conversation memory with a TTL. **Amazon SES** sends the developer briefing.
- The web chat is served from a Lambda Function URL from the same function.
- Everything deploys from one plain CloudFormation template and a shell script.

**AWS CDS services used at runtime:** AWS End User Messaging Social (WhatsApp), Amazon SES, and AWS End User Messaging SMS/RCS (wired). Plus Amazon Bedrock, Polly, Lambda, SNS, DynamoDB and S3.

## Cost
Measured on the live agent: about 1 to 2 cents of AI per reply, and about 3 cents all-in at list prices including WhatsApp delivery and a voice note. Pay per use, no monthly chatbot platform fee, and the agent, its prompts and its conversation data live in the business's own AWS account.

## Challenges we ran into
- **Meta business verification.** Our first WhatsApp Business Account sat under a portfolio whose verification had been rejected, so linking failed with an unhelpful "unverified WABA" error. Moving to a clean portfolio fixed it in minutes.
- **Phone number formats.** The WhatsApp webhook gives the sender as a bare number, but EUM Social wants E.164 with a plus sign. Every reply failed until we normalized it.
- **A bilingual voice.** Neural Polly voices ignore SSML language tags, so French words came out with an English accent. Lucienne now marks her French in her own replies, and we stitch Léa (French) and Amy (English) segments into one MP3.
- **Silent voice-note drops.** The stitched MP3 sent fine but never arrived: each Polly segment carries an ID3 tag, and tags mid-stream made WhatsApp drop the file. Stripping them fixed it.

## Accomplishments that we're proud of
A real, working conversation on WhatsApp that inspects a live site in seconds and explains it like a person would, with a voice and a personality, for about 3 cents a reply.

## What we learned
Conversation beats dashboards for small business owners. Ranking findings by impact and sizing them for a chat bubble mattered more than adding checks.

## What's next
- SMS and RCS go live once toll-free registration clears.
- Scheduled re-checks that message the owner when something breaks.
- Onboarding our existing web-design clients in Panama as the first customers, through Hero Apps.

## Try it
- **Web chat (no setup):** https://3aeprrnzvxpaum6k7vq4qccvd40pcngi.lambda-url.us-east-1.on.aws/
- **WhatsApp:** +1 857 754 4505 (https://wa.me/18577544505)
- **Landing page:** https://lucienne.hero-apps.com
- **Code (MIT):** https://github.com/tanDivina/lucienne
