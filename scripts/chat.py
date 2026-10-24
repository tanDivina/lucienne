#!/usr/bin/env python3
"""Local CLI chat with Lucienne — talks to Bedrock directly, no deploy needed.

Usage: python3 scripts/chat.py            (interactive)
       python3 scripts/chat.py "audit hero-apps.com"
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("REPORT_FROM", "dorien.vda@gmail.com")
os.environ.setdefault("ALLOWED_REPORT_RECIPIENTS", "dorien.vda@gmail.com")

from agent import run_turn  # noqa: E402

session = f"cli:{os.getpid()}"
args = " ".join(sys.argv[1:])

if args:
    print(run_turn(session, "web", args))
else:
    print("Lucienne CLI — ctrl-d to exit")
    while True:
        try:
            text = input("\nyou> ").strip()
        except EOFError:
            break
        if text:
            print("\nlucienne>", run_turn(session, "web", text))
