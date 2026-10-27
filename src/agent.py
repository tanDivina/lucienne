"""Lucienne's agentic core: a Bedrock Converse tool-use loop.

One entry point — run_turn(session_id, channel, user_text) — shared by every
channel (RCS/SMS webhook, web chat demo, CLI). Conversation history is kept in
DynamoDB keyed by session, so a texted "yes, email me the full report" works
across Lambda invocations.
"""

from __future__ import annotations

import json
import os
import re
import time

import boto3

from seo_tools import check_robots_sitemap, core_web_vitals, inspect_page

MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
TABLE = os.environ.get("SESSIONS_TABLE", "")
REPORT_FROM = os.environ.get("REPORT_FROM", "")
ALLOWED_REPORT_RECIPIENTS = [
    e.strip().lower()
    for e in os.environ.get("ALLOWED_REPORT_RECIPIENTS", "").split(",")
    if e.strip()
]
MAX_TOOL_ROUNDS = 8
MAX_HISTORY_MESSAGES = 20

_bedrock = boto3.client("bedrock-runtime")
_ses = boto3.client("sesv2")
_ddb = boto3.resource("dynamodb")

SYSTEM_PROMPT = """You are Lucienne, a conversational website & SEO copilot. Your name \
comes from lux/luz: you bring light and clarity to what is really going on inside a \
website. You speak like a meticulous, friendly senior inspector: warm, precise, zero \
jargon unless asked, with a refined European touch. You never pad, never use filler \
hype, and you always translate technical findings into what they mean for the site \
owner's visitors and search rankings. A light French touch is part of your charm: now \
and then - not every reply - open with a small interjection such as "Alors,", "Voila -" \
or "Bon,". Never write whole sentences in French. RULE, no exceptions: every French \
word or phrase, including the very first word of a reply, is wrapped in single \
underscores - _Mais oui!_, _Alors_, _Voilà_, _un petit peu_. The underscores make it \
italic on WhatsApp and tell your voice to pronounce it in French; unmarked French gets \
read with an English accent. Never use underscores for anything else, and never \
mention or explain them to the user.

You are talking over a messaging channel ({channel}), so:
- Keep replies SHORT: 2-6 sentences or a tight bullet list. Hard limit ~900 characters \
unless the user asks for depth.
- Plain text only. No markdown: no headers, tables, asterisks or bold. Simple dashes for lists are fine. On \
sms/rcs channels, emoji traffic lights (green/yellow/red circles) help scanability; on web, use them sparingly.
- One clear next step or question at the end when natural.

Working method:
- When the user gives you a URL, call inspect_page first. Call check_robots_sitemap \
when indexing could be at play, and core_web_vitals when speed matters or the user \
asks. Don't run every tool by reflex; fetch what the conversation needs.
- Lead with the two or three findings that matter most, ranked by impact, and say WHY \
each matters in plain words. Mention what is healthy in one short clause so the owner \
knows what not to touch.
- Offer the full developer briefing by email when there is real depth to share: \
"Want the full developer report by email?" If the user says yes and you have their \
address, call email_report with a focused, well-structured HTML report for developers: \
each finding ranked by impact with its evidence and the exact fix, in plain semantic HTML \
(headings, lists, short paragraphs, no inline styling). Keep it under about 700 words so \
it arrives quickly.
- Finish the work within this reply: never say you are "preparing" or "will send" \
something. Either call the tool now and confirm the result, or ask for what's missing.
- If a tool errors, say plainly what you could and couldn't check. Never invent data.
- Never guess where a business is or what it sells from its name or domain. Only name \
a country, town or offering that the page itself states; otherwise leave it out.
- You audit websites. When someone chats, teases or asks about you (your French, your \
lantern, how you work), play along warmly for a sentence with genuine charm and good \
humour, then gently invite them back with an offer to inspect a site. Never lecture \
people about what you are "not for". Only for real requests outside your craft (homework, \
unrelated tasks), kindly explain what you do instead.

Audit methodology (how to rank impact):
- Severity order: 1) crawlability and indexation (noindex, robots blocks, broken \
canonicals, 4xx/5xx, redirect loops) beats everything - if Google can't index the page, \
nothing else matters; 2) technical foundations (Core Web Vitals, HTTPS, mobile \
viewport, TTFB); 3) on-page basics (missing or weak title, meta description, single \
clear h1, image alts); 4) content depth and intent; 5) social/schema polish (Open \
Graph, JSON-LD). Rank your findings by this order, then by how far the value is from \
healthy.
- Healthy reference points: title ~50-60 chars, meta description ~150-160 chars, \
exactly one h1, LCP under 2.5s, INP under 200ms, CLS under 0.1. Treat these as guides, \
not laws - say when a deviation is harmless.
- You fetch raw HTML without executing JavaScript. If a page looks client-rendered \
(very low word count, empty h1s, framework roots), say that schema, content or tags \
may be injected by JavaScript that you cannot see - recommend Google's Rich Results \
Test to confirm - rather than asserting they are missing. Never report "no structured \
data" as a defect on a page that looks JS-rendered.
- Adapt to the site type when it is apparent. Local business or tours: completeness of \
contact info, LocalBusiness schema, language tags for bilingual audiences. Online \
store: product schema, thin or duplicated descriptions. Blog or content site: dated or \
thin articles, missing descriptions at scale. SaaS or app: thin feature pages, missing \
comparison content.
- In the email developer report, structure each finding as: what is wrong, impact \
(high/medium/low), evidence (the actual value you measured), and the specific fix. \
End the report with a prioritized action list: critical fixes first, then quick wins.

Today's context: you are a demo for the AWS CDS Agentic AI Hackathon, built by \
Divina Endeavors for Hero Apps. If asked who made you: Dorien Van den Abbeele."""

TOOLS = [
    {
        "toolSpec": {
            "name": "inspect_page",
            "description": "Fetch a web page and extract technical SEO signals: status, redirects, TTFB, page weight, title, meta description, canonical, robots meta, h1s, image alts, Open Graph, JSON-LD types, word count, noindex, lang.",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Page URL"}},
                "required": ["url"],
            }},
        }
    },
    {
        "toolSpec": {
            "name": "check_robots_sitemap",
            "description": "Check robots.txt and sitemap.xml for the site of the given URL: blanket disallows, declared sitemaps, sitemap URL count.",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            }},
        }
    },
    {
        "toolSpec": {
            "name": "core_web_vitals",
            "description": "Run Google PageSpeed Insights on a URL: performance score, lab LCP/CLS/TBT and real-user (CrUX) p75 LCP/INP/CLS when available. Takes 20-60s.",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "strategy": {"type": "string", "enum": ["mobile", "desktop"]},
                },
                "required": ["url"],
            }},
        }
    },
    {
        "toolSpec": {
            "name": "email_report",
            "description": "Send the full developer briefing as an HTML email via Amazon SES. Only use after the user asked for the report and gave an address.",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string"},
                    "html_body": {"type": "string", "description": "Complete HTML report"},
                },
                "required": ["to", "subject", "html_body"],
            }},
        }
    },
]


def email_report(to: str, subject: str, html_body: str) -> dict:
    if ALLOWED_REPORT_RECIPIENTS and to.lower() not in ALLOWED_REPORT_RECIPIENTS:
        return {
            "error": "This demo runs in the SES sandbox and can only email verified "
                     "addresses. Tell the user their address isn't verified for the demo yet.",
            "allowed": ALLOWED_REPORT_RECIPIENTS,
        }
    _ses.send_email(
        FromEmailAddress=REPORT_FROM,
        Destination={"ToAddresses": [to]},
        Content={"Simple": {
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": _lucienne_email(subject, html_body)}},
        }},
    )
    return {"sent": True, "to": to}


# Every report goes out in Lucienne's house style, whatever HTML the model wrote:
# her own styling is stripped and each tag gets inline styles (Gmail ignores most
# <style> blocks). Colors and type follow the landing page: paper, ink, lantern amber.
_EMAIL_ASSETS = "https://lucienne.hero-apps.com/assets"
_SERIF = "Georgia, 'Times New Roman', serif"
_TAG_STYLES = {
    "h1": f"font-family:{_SERIF};font-size:26px;line-height:1.25;font-weight:normal;color:#221c13;margin:28px 0 10px;",
    "h2": f"font-family:{_SERIF};font-size:21px;line-height:1.3;font-weight:normal;color:#221c13;margin:30px 0 8px;padding-top:18px;border-top:1px solid #e4dcc6;",
    "h3": f"font-family:{_SERIF};font-size:17px;line-height:1.35;font-weight:bold;color:#8a6d1f;margin:22px 0 6px;",
    "p": f"font-family:{_SERIF};font-size:16px;line-height:1.6;color:#221c13;margin:0 0 14px;",
    "ul": "margin:0 0 16px;padding-left:22px;",
    "ol": "margin:0 0 16px;padding-left:22px;",
    "li": f"font-family:{_SERIF};font-size:16px;line-height:1.6;color:#221c13;margin:0 0 8px;",
    "a": "color:#8a6d1f;text-decoration:underline;",
    "strong": "color:#221c13;",
    "code": "font-family:Menlo,Consolas,monospace;font-size:13px;background:#efe8d4;color:#5b4714;padding:1px 5px;border-radius:4px;",
    "pre": "font-family:Menlo,Consolas,monospace;font-size:13px;line-height:1.5;background:#efe8d4;color:#3a2f14;padding:14px 16px;border-radius:8px;white-space:pre-wrap;margin:0 0 16px;",
    "table": "border-collapse:collapse;width:100%;margin:0 0 18px;",
    "th": f"font-family:{_SERIF};font-size:14px;text-align:left;color:#8a6d1f;border-bottom:2px solid #d8c9a0;padding:8px 10px;",
    "td": f"font-family:{_SERIF};font-size:14px;color:#221c13;border-bottom:1px solid #e4dcc6;padding:8px 10px;vertical-align:top;",
    "blockquote": f"font-family:{_SERIF};font-style:italic;color:#5c5446;border-left:3px solid #c9a24a;margin:0 0 16px;padding:4px 0 4px 16px;",
    "hr": "border:0;border-top:1px solid #e4dcc6;margin:26px 0;",
}


def _restyle(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", "", html)
    html = re.sub(r"(?is)</?(html|body|!doctype)[^>]*>", "", html)
    html = re.sub(r'(?i)\s(style|class|bgcolor|color|face)\s*=\s*("[^"]*"|\'[^\']*\')', "", html)
    for tag, style in _TAG_STYLES.items():
        html = re.sub(rf"(?i)<{tag}(\s[^>]*)?>", lambda m, t=tag, s=style: f'<{t}{m.group(1) or ""} style="{s}">', html)
    return html.strip()


def _lucienne_email(subject: str, html_body: str) -> str:
    body = _restyle(html_body)
    title = re.sub(r"[<>&\"]", "", subject)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f3efe1;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3efe1;">
<tr><td align="center" style="padding:32px 14px;">
  <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">
    <tr><td align="center" style="padding:0 0 22px;">
      <img src="{_EMAIL_ASSETS}/apple-touch-icon.png" width="88" height="88" alt="Lucienne"
        style="display:block;border-radius:50%;border:4px solid #ecdcae;">
      <div style="font-family:{_SERIF};font-size:30px;color:#221c13;margin-top:12px;">Lucienne</div>
      <div style="font-family:{_SERIF};font-size:12px;letter-spacing:3px;text-transform:uppercase;color:#8a6d1f;margin-top:4px;">Developer briefing</div>
    </td></tr>
    <tr><td style="background:#faf7ec;border:1px solid #e4dcc6;border-radius:14px;padding:30px 34px;">
      <div style="font-family:{_SERIF};font-size:22px;line-height:1.3;color:#221c13;margin:0 0 18px;">{title}</div>
      {body}
    </td></tr>
    <tr><td align="center" style="padding:24px 10px 0;">
      <div style="font-family:{_SERIF};font-style:italic;font-size:16px;color:#5c5446;">Voil&agrave;. Questions? Just reply in the chat, I remember our conversation.</div>
      <div style="font-family:{_SERIF};font-size:13px;color:#7b7161;margin-top:10px;">
        Lucienne, website &amp; SEO copilot &middot;
        <a href="https://lucienne.hero-apps.com" style="color:#8a6d1f;">lucienne.hero-apps.com</a> &middot;
        WhatsApp +1 857 754 4505</div>
      <div style="font-family:{_SERIF};font-size:11px;color:#9c9280;margin-top:8px;">Built on Amazon Bedrock, AWS End User Messaging and Amazon SES.</div>
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


_LOCAL_TOOLS = {
    "inspect_page": lambda args: inspect_page(**args),
    "check_robots_sitemap": lambda args: check_robots_sitemap(**args),
    "core_web_vitals": lambda args: core_web_vitals(**args),
    "email_report": lambda args: email_report(**args),
}


_local_sessions: dict[str, list] = {}  # fallback when no DynamoDB table (CLI/testing)


def _sanitize(messages: list) -> list:
    """Return the history if Bedrock will accept it, else start fresh.
    Valid: roles strictly alternate starting with 'user', every assistant
    tool_use is answered by tool_results with matching ids in the next
    message, and the history ends on an assistant message without tool_use."""
    def tool_use_ids(msg):
        return {c["toolUse"]["toolUseId"] for c in msg.get("content", []) if "toolUse" in c}

    def tool_result_ids(msg):
        return {c["toolResult"]["toolUseId"] for c in msg.get("content", []) if "toolResult" in c}

    if not messages:
        return []
    ok = messages[-1].get("role") == "assistant" and not tool_use_ids(messages[-1])
    for i, msg in enumerate(messages):
        expected = "user" if i % 2 == 0 else "assistant"
        if msg.get("role") != expected or not msg.get("content"):
            ok = False
            break
        if expected == "user" and i > 0 and tool_result_ids(msg) != tool_use_ids(messages[i - 1]):
            ok = False
            break
    return messages if ok else []


def _truncate(messages: list) -> list:
    """Keep roughly the last MAX_HISTORY_MESSAGES, cutting only at a plain
    user-text boundary so tool call/result pairs are never split."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    for i in range(len(messages) - MAX_HISTORY_MESSAGES, len(messages)):
        m = messages[i]
        if m.get("role") == "user" and not any("toolResult" in c for c in m.get("content", [])):
            return messages[i:]
    return messages[-2:]  # degenerate: keep just the last exchange


def _load_history(session_id: str) -> list:
    if not TABLE:
        return _sanitize(_local_sessions.get(session_id, []))
    item = _ddb.Table(TABLE).get_item(Key={"session_id": session_id}).get("Item")
    return _sanitize(json.loads(item["messages"])) if item else []


def _save_history(session_id: str, messages: list) -> None:
    messages = _truncate(messages)
    if not TABLE:
        _local_sessions[session_id] = messages
        return
    _ddb.Table(TABLE).put_item(Item={
        "session_id": session_id,
        "messages": json.dumps(messages),
        "expires_at": int(time.time()) + 7 * 24 * 3600,
    })


# The prompt forbids markdown but the model still slips some in; scrub it
# deterministically so no channel ever shows asterisks or hashes.
_MD_RULES = [
    (re.compile(r"^#{1,6}\s+", re.M), ""),                     # headings
    (re.compile(r"\*\*\*(.+?)\*\*\*", re.S), r"\1"),           # bold italic
    (re.compile(r"\*\*(.+?)\*\*", re.S), r"\1"),               # bold
    (re.compile(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])"), r"\1"), # italic
    (re.compile(r"__(.+?)__", re.S), r"\1"),
    # Single _underscores_ are kept: they mark French (WhatsApp italics + French voice).
    (re.compile(r"```[a-z]*\n?"), ""),                         # code fences
    (re.compile(r"`([^`\n]*)`"), r"\1"),                       # inline code
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"), r"\1 (\2)"),    # links
    (re.compile(r"^(\s*)[*•]\s+", re.M), r"\1- "),             # bullets -> dashes
    (re.compile(r"^\s*>\s?", re.M), ""),                       # blockquotes
    (re.compile(r"^\s*(?:-{3,}|={3,}|\*{3,}|_{3,})\s*$", re.M), ""), # rules
]


def _strip_markdown(text: str) -> str:
    for pat, rep in _MD_RULES:
        text = pat.sub(rep, text)
    return text.strip()


def run_turn(session_id: str, channel: str, user_text: str) -> str:
    """One conversational turn. Returns Lucienne's reply text."""
    messages = _load_history(session_id)
    messages.append({"role": "user", "content": [{"text": user_text[:4000]}]})

    reply = ""
    for _ in range(MAX_TOOL_ROUNDS):
        resp = _bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT.format(channel=channel)}],
            messages=messages,
            toolConfig={"tools": TOOLS},
            inferenceConfig={"maxTokens": 16000, "temperature": 0.4},
        )
        msg = resp["output"]["message"]
        messages.append(msg)
        print(f"round stop={resp.get('stopReason')} blocks={[list(c)[0] for c in msg['content']]}")

        if resp.get("stopReason") != "tool_use":
            reply = " ".join(
                c["text"] for c in msg["content"] if "text" in c
            ).strip()
            break

        results = []
        for block in msg["content"]:
            if "toolUse" not in block:
                continue
            tu = block["toolUse"]
            fn = _LOCAL_TOOLS.get(tu["name"])
            try:
                out = fn(tu["input"]) if fn else {"error": f"unknown tool {tu['name']}"}
            except Exception as e:  # noqa: BLE001 - surface tool crashes to the model
                out = {"error": f"{e.__class__.__name__}: {e}"}
            results.append({"toolResult": {
                "toolUseId": tu["toolUseId"],
                "content": [{"json": out}],
            }})
        messages.append({"role": "user", "content": results})
    else:
        reply = "I hit my inspection budget for one message - ask me to continue and I'll pick up where I left off."
        messages.append({"role": "assistant", "content": [{"text": reply}]})

    _save_history(session_id, messages)
    return _strip_markdown(reply) or "(no reply)"
