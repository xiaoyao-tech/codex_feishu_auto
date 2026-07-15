#!/usr/bin/env python3
"""Check portable dependencies without reading credentials."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def command_check(name: str, required: bool = True) -> dict[str, object]:
    path = shutil.which(name)
    return {"name": name, "ok": bool(path), "required": required, "path": path or ""}


def config_check(path: Path) -> dict[str, object]:
    result: dict[str, object] = {"name": "config", "ok": False, "required": True, "path": str(path)}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        mode = config.get("mode")
        if mode not in {"live-event", "topic-duty", "ops-check"}:
            raise ValueError(f"unsupported mode: {mode}")
        ZoneInfo(config.get("timezone", "Asia/Shanghai"))
        result.update({"ok": True, "mode": mode})
    except (OSError, json.JSONDecodeError, ValueError, ZoneInfoNotFoundError) as exc:
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Check codex-feishu-auto dependencies.")
    parser.add_argument("--config", help="Optional config.json to validate.")
    parser.add_argument("--capture", action="store_true", help="Require macOS capture dependencies.")
    parser.add_argument("--skip-lark", action="store_true", help="Do not require lark-cli.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    checks: list[dict[str, object]] = [
        {
            "name": "python>=3.9",
            "ok": sys.version_info >= (3, 9),
            "required": True,
            "version": platform.python_version(),
        },
        command_check("git", required=False),
        command_check("curl", required=False),
    ]
    if not args.skip_lark:
        checks.append(command_check("lark-cli", required=True))
    if args.capture:
        checks.append(
            {
                "name": "macOS",
                "ok": platform.system() == "Darwin",
                "required": True,
                "platform": platform.platform(),
            }
        )
        checks.extend(command_check(name, required=True) for name in ("zsh", "osascript", "screencapture", "swift", "shasum"))
    if args.config:
        checks.append(config_check(Path(args.config).expanduser().resolve()))

    ok = all(bool(check["ok"]) for check in checks if check.get("required"))
    payload = {
        "ok": ok,
        "checks": checks,
        "notes": [
            "This doctor does not inspect or print Feishu credentials.",
            "Screen Recording permission must still be granted interactively on macOS.",
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("codex-feishu-auto doctor")
        for check in checks:
            mark = "OK" if check["ok"] else "MISSING"
            required = "required" if check.get("required") else "optional"
            print(f"- [{mark}] {check['name']} ({required})")
        for note in payload["notes"]:
            print(f"- note: {note}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
