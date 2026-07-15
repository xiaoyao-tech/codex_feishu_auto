#!/usr/bin/env python3
"""Send a local alert and optionally a confirmed Feishu message."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time


DEFAULT_SOUND = "/System/Library/Sounds/Glass.aiff"


def run(argv: list[str]) -> bool:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def local_alert(title: str, message: str, repeat: int, no_sound: bool) -> dict[str, object]:
    result: dict[str, object] = {"notification": False, "sound": False, "bell": False}
    if shutil.which("osascript"):
        script = f"display notification {applescript_string(message)} with title {applescript_string(title)}"
        result["notification"] = run(["osascript", "-e", script])
    if not no_sound and shutil.which("afplay") and os.path.exists(DEFAULT_SOUND):
        played = 0
        for _ in range(max(1, repeat)):
            if run(["afplay", DEFAULT_SOUND]):
                played += 1
            time.sleep(0.2)
        result["sound"] = played > 0
        result["sound_repeats"] = played
    if not result["sound"]:
        sys.stdout.write("\a")
        sys.stdout.flush()
        result["bell"] = True
    return result


def lark_alert(chat_id: str, identity: str, title: str, message: str) -> dict[str, object]:
    if not chat_id:
        return {"attempted": False, "reason": "no confirmed chat id"}
    if not shutil.which("lark-cli"):
        return {"attempted": False, "reason": "lark-cli not found"}
    ok = run(
        [
            "lark-cli",
            "im",
            "+messages-send",
            "--chat-id",
            chat_id,
            "--text",
            f"{title}\n\n{message}",
            "--as",
            identity,
        ]
    )
    return {"attempted": True, "ok": ok, "identity": identity}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local and optional Feishu alert.")
    parser.add_argument("--title", default="Codex automation alert")
    parser.add_argument("--message", required=True)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--no-sound", action="store_true")
    parser.add_argument("--no-local", action="store_true")
    parser.add_argument("--lark-chat-id", default=os.environ.get("CODEX_FEISHU_ALERT_CHAT_ID", ""))
    parser.add_argument("--lark-as", choices=("user", "bot"), default=os.environ.get("CODEX_FEISHU_ALERT_AS", "bot"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.dry_run:
        payload = {
            "dry_run": True,
            "local_enabled": not args.no_local,
            "lark_configured": bool(args.lark_chat_id),
            "identity": args.lark_as,
            "title": args.title,
            "message": args.message,
        }
    else:
        payload = {
            "local": {"attempted": False} if args.no_local else local_alert(args.title, args.message, args.repeat, args.no_sound),
            "lark": lark_alert(args.lark_chat_id, args.lark_as, args.title, args.message),
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
