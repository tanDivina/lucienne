## Inspiration
I build websites for small businesses in Bocas del Toro, Panama, through my studio Hero Apps, and almost none of them can afford an SEO agency (0:03). A retainer runs about $3,000 a month (Ahrefs puts the average at $2,819, Arc Intermedia at about $3,200). The free tools hand owners a dashboard of red numbers nobody explains, and 57% of small businesses have no SEO strategy at all, according to an UpCity/Pollfish survey of 600 US and Canadian small businesses (0:12). Page two of Google gets about 0.17% of clicks (Sistrix, 80 million keywords). My clients don't open dashboards. They live in WhatsApp, so I made the audit a WhatsApp conversation.

Hero Apps is my own company, and it is the customer on the ACE opportunity. Lucienne's first outside site is my partner's boat tour company, Papito's Nature Tours.

The demo video is at the top of this page (2:51). The timestamps below point to the moment in it.

## What it does
Lucienne is a French SEO inspector you can text (0:30). Send her a website address on WhatsApp and she inspects the live page, then explains what she found in plain words, ranked by impact and short enough for a chat bubble. In the demo (0:36) I send her panacacao.com, a site I built, from my own phone:

- She fetches the live page and replies with the audit (0:41). The real reply took 13.5 seconds.
- She follows each reply with a voice note (0:48). French phrases are spoken by a French voice and the rest in English.
- I ask her to check the speed (1:05). She runs Google PageSpeed Insights and reports a mobile Largest Contentful Paint of 5.9 seconds, with why it matters (1:08). That reply took 22.5 seconds.
- She remembers the conversation, so "why does that matter?" or "how do I fix it?" gets an answer in context.
- The same agent runs a web chat with voice and microphone input (1:29). Her lantern glows while she inspects.
- Ask for the full report and an HTML developer briefing arrives by email through Amazon SES (1:41), with each finding's impact, evidence and fix, ready to forward to whoever builds the site.

WhatsApp, the web chat and email are live (1:52). SMS and RCS go through the same handler and are waiting on toll-free carrier registration.

Her checks: HTTP status, redirects, time to first byte, page weight, title, meta description, canonical, robots meta, headings, image alt text, Open Graph, JSON-LD and noindex on the page; robots.txt and sitemap health; and Core Web Vitals from PageSpeed Insights, with lab and real-user data.

## How I built it (2:05)
- AWS End User Messaging Social receives WhatsApp messages and delivers them through Amazon SNS to an AWS Lambda written in Python with only the standard library.
- The Lambda runs a Bedrock Converse tool-use loop with Claude Sonnet 4.5 and four tools: `inspect_page`, `check_robots_sitemap`, `core_web_vitals` and `email_report`.
- Replies go back through `SendWhatsAppMessage`. Amazon Polly renders the voice note, which is uploaded with `PostWhatsAppMessageMedia` (staged in Amazon S3) and sent as audio.
- Amazon DynamoDB keeps the conversation memory with a TTL. Amazon SES sends the developer briefing.
- The web chat is served by the same function through a Lambda Function URL.
- Everything deploys from one CloudFormation template and a shell script.

AWS CDS services used at runtime: AWS End User Messaging Social (WhatsApp) and Amazon SES, with AWS End User Messaging SMS/RCS wired. Plus Amazon Bedrock, Polly, Lambda, SNS, DynamoDB and S3.

## Cost (2:23)
Measured on the live agent: about 1 to 2 cents of AI per reply, and about 3 cents with WhatsApp delivery and a voice note, at list prices. Billing is per use, with no monthly chatbot platform fee, and the agent, its prompts and its conversation data live in the business's own AWS account.

## Challenges I ran into
- **Meta business verification.** My first WhatsApp Business Account sat under a portfolio whose verification had been rejected, so linking failed with an "unverified WABA" error. Moving to a clean portfolio fixed it in minutes.
- **Phone number formats.** The WhatsApp webhook gives the sender as a bare number, and EUM Social wants E.164 with a plus sign. Every reply failed until I normalized it.
- **A bilingual voice.** Neural Polly voices ignore SSML language tags, so French words came out with an English accent. Lucienne now marks her French in her own replies, and I stitch Léa (French) and Amy (English) segments into one MP3.
- **Voice notes that never arrived.** The stitched MP3 sent without an error and never reached the phone, because each Polly segment carries an ID3 tag and tags in the middle of the file made WhatsApp drop it. Stripping them fixed it.

## What I learned
Small business owners act on a few findings ranked by impact and sized for a chat bubble. That mattered more than adding checks.

## What's next (2:34)
- Papito's Nature Tours, whose site she is already auditing, then the tour operators and small businesses I build websites for.
- SMS and RCS once toll-free registration clears.
- Scheduled re-checks that message the owner when something on the site breaks.
- Moving the tool loop and memory to Bedrock AgentCore Runtime and Memory.

## Try it
- Web chat, no setup: https://3aeprrnzvxpaum6k7vq4qccvd40pcngi.lambda-url.us-east-1.on.aws/
- WhatsApp: +1 857 754 4505 (https://wa.me/18577544505)
- Landing page: https://lucienne.hero-apps.com
- Code (MIT): https://github.com/tanDivina/lucienne

Amazon SES for this account is still in the sandbox, so the emailed report only reaches my verified addresses. The WhatsApp and web chat audits work for everyone.
