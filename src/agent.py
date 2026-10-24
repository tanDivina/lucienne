"""Lucienne's agentic core: a Bedrock Converse tool-use loop.

One entry point — run_turn(session_id, channel, user_text) — shared by every
channel (RCS/SMS webhook, web chat demo, CLI). Conversation history is kept in
DynamoDB keyed by session, so a texted "yes, email me the full report" works
across Lambda invocations.
"""

from __future__ import annotations

import json
import os
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
owner's visitors and search rankings.

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
address, call email_report with a thorough, well-structured HTML report (that report \
CAN be long and technical - it is for developers).
- Finish the work within this reply: never say you are "preparing" or "will send" \
something. Either call the tool now and confirm the result, or ask for what's missing.
- If a tool errors, say plainly what you could and couldn't check. Never invent data.
- You audit websites; politely decline unrelated requests and steer back.

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
            "Body": {"Html": {"Data": html_body}},
        }},
    )
    return {"sent": True, "to": to}


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
    return reply or "(no reply)"
