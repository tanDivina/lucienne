#!/usr/bin/env python3
"""Plays the Lucienne demo conversation on the plugged-in phone (WhatsApp
Business app, chat with Lucienne) while scripts/record-whatsapp.sh records.
After each text reply it waits for her voice note and taps play, so her real
Polly voice is in the recording.

Types each message word by word over adb, taps Send, then waits for the live
agent's reply by watching the guest's conversation item in DynamoDB, plus a
pause so the reply can be read on camera. Writes a timeline (seconds since
start) next to the recording for captions.
Usage: python3 drive_whatsapp.py [timeline.json]
"""
import json
import os
import re
import subprocess
import sys
import time

ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
PKG = "com.whatsapp.w4b"
GUEST = "+50767450876"
TABLE = "lucienne-sessions"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/Lucienne_Video/v3_work/whatsapp_timeline.json")

# (text, seconds to read the reply, seconds of voice note to let play)
MESSAGES = [
    ("panacacao.com", 5.0, 13.0),
    ("Yes, check the speed please", 5.0, 10.0),
]


def adb(*args, capture=False):
    r = subprocess.run([ADB, "shell", *args], capture_output=True, text=True)
    return r.stdout if capture else None


def bounds(resource_id):
    adb("uiautomator", "dump", "/sdcard/ui.xml")
    xml = subprocess.run([ADB, "exec-out", "cat", "/sdcard/ui.xml"], capture_output=True, text=True).stdout
    for node in re.findall(r"<node [^>]*>", xml):
        if f'resource-id="{PKG}:id/{resource_id}"' in node:
            x1, y1, x2, y2 = map(int, re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node).groups())
            return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def assistant_turns():
    r = subprocess.run(["aws", "dynamodb", "get-item", "--region", "us-east-1", "--table-name", TABLE,
                        "--key", json.dumps({"session_id": {"S": f"wa:{GUEST}"}}), "--output", "json"], capture_output=True, text=True)
    try:
        msgs = json.loads(json.loads(r.stdout)["Item"]["messages"]["S"])
    except Exception:
        return 0
    # a finished reply = assistant turn with a text block (Bedrock Converse format)
    return sum(1 for m in msgs if m.get("role") == "assistant" and any("text" in b for b in m.get("content", [])))


def play_buttons():
    """Centres of the voice-note play buttons currently on screen, top to bottom."""
    adb("uiautomator", "dump", "/sdcard/ui.xml")
    xml = subprocess.run([ADB, "exec-out", "cat", "/sdcard/ui.xml"], capture_output=True, text=True).stdout
    out = []
    for node in re.findall(r"<node [^>]*>", xml):
        if re.search(r'content-desc="(Play|Reproducir)[^"]*"', node) or f'resource-id="{PKG}:id/control_btn"' in node:
            x1, y1, x2, y2 = map(int, re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node).groups())
            out.append(((x1 + x2) // 2, (y1 + y2) // 2))
    return sorted(out, key=lambda p: p[1])


def type_words(text):
    words = text.split(" ")
    for i, w in enumerate(words):
        chunk = w + (" " if i < len(words) - 1 else "")
        adb("input", "text", chunk.replace(" ", "%s").replace("'", ""))
        time.sleep(0.18)


def main():
    t0 = time.time()
    now = lambda: round(time.time() - t0, 2)
    timeline = []
    entry = bounds("entry")
    if not entry:
        sys.exit("WhatsApp chat input not found: open the Don Tuco chat first")
    time.sleep(2.0)
    for text, read_pause, voice_secs in MESSAGES:
        before = assistant_turns()
        before_btns = len(play_buttons())
        entry = bounds("entry") or entry  # the box moves when the keyboard opens
        adb("input", "tap", str(entry[0]), str(entry[1]))
        time.sleep(0.4)
        type_words(text)
        time.sleep(0.6)
        send = bounds("send")
        for _ in range(3):  # the keyboard can still be animating in
            if send:
                break
            time.sleep(0.8)
            send = bounds("send")
        if not send:
            sys.exit(f"Send button not found after typing: {text!r}")
        adb("input", "tap", str(send[0]), str(send[1]))
        sent = now()
        print(f"→ {sent:6.1f}s sent: {text}", flush=True)
        deadline = time.time() + 90
        while assistant_turns() <= before and time.time() < deadline:
            time.sleep(0.7)
        replied = now()
        print(f"← {replied:6.1f}s reply stored ({replied - sent:.1f}s)", flush=True)
        time.sleep(read_pause)
        # Her voice note follows the text: wait for a new play button, tap the newest.
        vdeadline = time.time() + 40
        btns = play_buttons()
        while len(btns) <= before_btns and time.time() < vdeadline:
            time.sleep(1.0)
            btns = play_buttons()
        if not btns:
            btns = play_buttons()
        played = None
        if btns:
            x, y = btns[-1]
            adb("input", "tap", str(x), str(y))
            played = now()
            print(f"▶ {played:6.1f}s voice note playing", flush=True)
            time.sleep(voice_secs)
        timeline.append({"text": text, "sent": sent, "replied": replied, "voice_play": played})
    with open(OUT, "w") as f:
        json.dump({"messages": timeline, "total": now()}, f, indent=2)
    print(f"timeline → {OUT}")


if __name__ == "__main__":
    main()
