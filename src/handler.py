"""Lambda entry point for Lucienne.

Routes four event shapes to the same agent core:
- SNS notifications from AWS End User Messaging two-way SMS/RCS -> reply over SMS/RCS
- SNS notifications from AWS End User Messaging Social (WhatsApp) -> reply on WhatsApp
- Function URL GET /            -> the web chat demo page
- Function URL POST /chat       -> JSON chat API used by the demo page
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import uuid

import boto3

from agent import run_turn

ORIGINATION_IDENTITY = os.environ.get("ORIGINATION_IDENTITY", "")
_sms = boto3.client("pinpoint-sms-voice-v2")
_polly = boto3.client("polly")

_WEB_DIR = pathlib.Path(__file__).parent / "web"
_ASSET_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}


def _handle_inbound_message(record: dict) -> None:
    """One inbound message from End User Messaging via SNS: WhatsApp or SMS/RCS."""
    msg = json.loads(record["Sns"]["Message"])
    if "whatsAppWebhookEntry" in msg:
        _handle_whatsapp(msg)
    else:
        _handle_sms(msg)


_social = None
_s3 = None


def _social_client():
    global _social
    if _social is None:
        _social = boto3.client("socialmessaging")
    return _social


def _s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def _handle_whatsapp(msg: dict) -> None:
    """One EUM Social webhook event (Meta entry, JSON-string wrapped)."""
    entry = msg.get("whatsAppWebhookEntry") or "{}"
    if isinstance(entry, str):
        entry = json.loads(entry)
    # Reply from the number the message arrived on; env var overrides.
    origination = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    if not origination:
        ids = (msg.get("context") or {}).get("MetaPhoneNumberIds") or []
        if ids:
            origination = (ids[0].get("arn") or "").rsplit("/", 1)[-1]

    for change in entry.get("changes", []):
        value = change.get("value") or {}
        for inbound in value.get("messages", []):  # absent on delivery-status events
            sender = inbound.get("from", "")
            if not sender or not origination:
                print("whatsapp event missing sender or origination:", json.dumps(msg)[:500])
                continue
            text = ((inbound.get("text") or {}).get("body") or "").strip()
            if text:
                reply = run_turn(session_id=f"wa:{sender}", channel="whatsapp", user_text=text)
            else:  # image/audio/sticker/...
                reply = ("Bonjour! For now I only read text here - "
                         "send me a website address and I will inspect it.")
            # WhatsApp caps a text message at 4096 chars.
            for chunk in [reply[i:i + 3800] for i in range(0, len(reply), 3800)] or ["..."]:
                _social_client().send_whatsapp_message(
                    originationPhoneNumberId=origination,
                    metaApiVersion="v20.0",
                    message=json.dumps({
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": sender,
                        "type": "text",
                        "text": {"preview_url": False, "body": chunk},
                    }).encode(),
                )
            if text:
                _send_whatsapp_voice(origination, sender, reply)


def _send_whatsapp_voice(origination: str, recipient: str, reply: str) -> None:
    """Lucienne's spoken headline as a WhatsApp audio message.

    Meta only takes media from S3, so: Polly mp3 -> media bucket (1-day
    lifecycle) -> PostWhatsAppMessageMedia -> audio message by media id.
    """
    bucket = os.environ.get("WA_MEDIA_BUCKET", "")
    if not bucket:
        return
    try:
        audio = _synthesize_bytes(reply)
        if not audio:
            return
        key = f"polly/{uuid.uuid4().hex}.mp3"
        _s3_client().put_object(Bucket=bucket, Key=key, Body=audio,
                                ContentType="audio/mpeg")
        media = _social_client().post_whatsapp_message_media(
            originationPhoneNumberId=origination,
            sourceS3File={"bucketName": bucket, "key": key},
        )
        _social_client().send_whatsapp_message(
            originationPhoneNumberId=origination,
            metaApiVersion="v20.0",
            message=json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "audio",
                "audio": {"id": media["mediaId"]},
            }).encode(),
        )
    except Exception as exc:  # voice is a garnish; never fail the text reply over it
        print("whatsapp voice error:", exc)


def _handle_sms(msg: dict) -> None:
    """One inbound SMS/RCS message from End User Messaging via SNS."""
    sender = msg.get("originationNumber")
    text = (msg.get("messageBody") or "").strip()
    if not sender or not text:
        print("inbound message missing sender or body:", json.dumps(msg)[:500])
        return

    reply = run_turn(session_id=f"sms:{sender}", channel="sms/rcs", user_text=text)

    origination = ORIGINATION_IDENTITY or msg.get("destinationNumber")
    # SMS segments are precious; the agent aims short but we hard-cap defensively.
    for chunk in [reply[i:i + 1500] for i in range(0, len(reply), 1500)] or ["..."]:
        _sms.send_text_message(
            DestinationPhoneNumber=sender,
            OriginationIdentity=origination,
            MessageBody=chunk,
            MessageType="TRANSACTIONAL",
        )


_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()


def _int_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + (("-" + _ONES[n % 10]) if n % 10 else "")
    if n < 1000:
        return _ONES[n // 100] + " hundred" + ((" " + _int_words(n % 100)) if n % 100 else "")
    for div, word in ((10**9, "billion"), (10**6, "million"), (1000, "thousand")):
        if n >= div:
            rest = (" " + _int_words(n % div)) if n % div else ""
            return _int_words(n // div) + " " + word + rest
    return str(n)


def _num_words(m: re.Match) -> str:
    tok = m.group(0).replace(",", "")
    if "." in tok:
        whole, frac = tok.split(".")
        return _int_words(int(whole)) + " point " + " ".join(_ONES[int(d)] for d in frac)
    n = int(tok)
    return _int_words(n) if n < 10**12 else tok


_SPOKEN = [  # the French voice reads digits and acronyms in French; hand her English words
    (r"https?://([^/\s]+)\S*", r"\1"),
    (r"[*_#`]", ""),
    (r"\bLCP\b", "Largest Contentful Paint"),
    (r"\bCLS\b", "Cumulative Layout Shift"),
    (r"\bINP\b", "Interaction to Next Paint"),
    (r"\bTTFB\b", "time to first byte"),
    (r"\bSEO\b", "search engine optimization"),
    (r"\bURLs\b", "links"),
    (r"\bURL\b", "link"),
    (r"\bh1\b", "main heading"),
    (r"\$\s*([\d,]+(?:\.\d+)?)", r"\1 dollars"),
    (r"\bCWV\b", "Core Web Vitals"),
    (r"\bEst\.", "Estimated"),  # Léa reads a bare "est" as French for "is"
    (r"\be\.g\.", "for example"),
    (r"\bi\.e\.", "that is"),
    (r"\bvs\b\.?", "versus"),
    (r"(\d)\s*/\s*(100|10|5)\b", r"\1 out of \2"),
    (r"(\w)/mo\b", r"\1 per month"),
    (r"(\w)/yr\b", r"\1 per year"),
    (r"(\d)\s*ms\b", r"\1 milliseconds"),
    (r"(\d)\s*s\b", r"\1 seconds"),
    (r"(\d)\s*(KB|kb)\b", r"\1 kilobytes"),
    (r"(\d)\s*(MB|mb)\b", r"\1 megabytes"),
    (r"%", " percent"),
    (r"&", " and "),
]


def _speechify(text: str) -> str:
    """Make a chat reply pleasant to hear from a French voice reading English."""
    for pat, rep in _SPOKEN:
        text = re.sub(pat, rep, text)
    text = re.sub(r"\d{1,3}(?:,\d{3})+|\d+\.\d+|\d+", _num_words, text)
    return text


def _speech_excerpt(text: str) -> str:
    """Speak a short headline, not the whole report; the chat holds the details."""
    text = text.strip()
    if len(text) <= 360:
        return text
    out = ""
    for para in text.split("\n"):
        p = para.strip()
        if not p or p.startswith(("-", "•", "*")):
            continue
        if out and len(out) + len(p) > 340:
            break
        out = (out + " " + p).strip()
        if len(out) >= 340:
            break
    if not out:  # reply was mostly bullets; never speak a mid-word slice
        head = text[:340]
        cut = max(head.rfind(". "), head.rfind("! "), head.rfind("? "), head.rfind(".\n"))
        out = head[: cut + 1].strip() if cut > 80 else head.rsplit(" ", 1)[0]
    return out + " ... The full details are in your chat."


def _synthesize_bytes(text: str) -> bytes | None:
    """Lucienne's voice: Polly's Léa (fr-FR neural) reading English = French accent."""
    try:
        resp = _polly.synthesize_speech(
            Engine="neural",
            VoiceId=os.environ.get("LUCIENNE_VOICE", "Lea"),
            OutputFormat="mp3",
            Text=_speechify(_speech_excerpt(text))[:2900],
        )
        return resp["AudioStream"].read()
    except Exception as exc:  # voice is a garnish; never fail the reply over it
        print("polly error:", exc)
        return None


def _synthesize(text: str) -> str | None:
    audio = _synthesize_bytes(text)
    return base64.b64encode(audio).decode() if audio else None


def _http_response(status: int, body: str, content_type: str = "application/json") -> dict:
    return {
        "statusCode": status,
        "headers": {
            "content-type": content_type,
            "access-control-allow-origin": "*",
            "access-control-allow-headers": "content-type",
            "access-control-allow-methods": "GET,POST,OPTIONS",
        },
        "body": body,
    }


def _handle_http(event: dict) -> dict:
    ctx = event.get("requestContext", {}).get("http", {})
    method, path = ctx.get("method", "GET"), ctx.get("path", "/")

    if method == "OPTIONS":
        return _http_response(204, "")

    if method == "GET":
        if "/assets/" in path:
            # basename only: no traversal, no subdirectories
            asset = _WEB_DIR / "assets" / pathlib.PurePosixPath(path).name
            if asset.suffix in _ASSET_TYPES and asset.is_file():
                return {
                    "statusCode": 200,
                    "headers": {
                        "content-type": _ASSET_TYPES[asset.suffix],
                        "cache-control": "public, max-age=86400",
                    },
                    "body": base64.b64encode(asset.read_bytes()).decode(),
                    "isBase64Encoded": True,
                }
            return _http_response(404, "no such asset", "text/plain")
        page = _WEB_DIR / "index.html"
        if page.exists():
            return _http_response(200, page.read_text(), "text/html; charset=utf-8")
        return _http_response(404, "demo page not bundled", "text/plain")

    if method == "POST" and path.rstrip("/").endswith("chat"):
        try:
            body = json.loads(event.get("body") or "{}")
            session_id = str(body["session_id"])[:100]
            message = str(body["message"])[:4000]
        except (KeyError, json.JSONDecodeError):
            return _http_response(400, json.dumps({"error": "need session_id and message"}))
        reply = run_turn(session_id=f"web:{session_id}", channel="web", user_text=message)
        payload = {"reply": reply}
        if body.get("speak"):
            audio = _synthesize(reply)
            if audio:
                payload["audio"] = audio
        return _http_response(200, json.dumps(payload))

    return _http_response(404, json.dumps({"error": "not found"}))


def lambda_handler(event: dict, _context) -> dict | None:
    if "Records" in event:  # SNS fan-in from End User Messaging
        for record in event["Records"]:
            if record.get("EventSource") == "aws:sns":
                _handle_inbound_message(record)
        return None
    if "requestContext" in event:  # Function URL
        return _handle_http(event)
    # Direct invoke (testing): {"session_id": "...", "message": "..."}
    return {"reply": run_turn(
        session_id=str(event.get("session_id", "direct")),
        channel=str(event.get("channel", "web")),
        user_text=str(event.get("message", "")),
    )}
