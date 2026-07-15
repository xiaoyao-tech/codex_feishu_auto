#!/usr/bin/env python3
"""Create a portable state directory for a Codex monitoring task."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULTS = {
    "live-event": {"normal_minutes": 30, "active_minutes": 1, "closeout_no_updates": 3},
    "topic-duty": {"normal_minutes": 30, "active_minutes": 15, "closeout_no_updates": 3},
    "ops-check": {"normal_minutes": 1440, "active_minutes": 1440, "closeout_no_updates": 0},
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-.").lower()
    return slug or "watch"


def parse_source(value: str) -> dict[str, str]:
    if "|" in value:
        name, target = value.split("|", 1)
    else:
        name, target = value, value
    name = name.strip()
    target = target.strip()
    if not name or not target:
        raise argparse.ArgumentTypeError("source must be 'name|URL or command description'")
    kind = "url" if target.startswith(("http://", "https://")) else "instruction"
    return {"name": name, "target": target, "kind": kind}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a stateful Codex + Feishu watch.")
    parser.add_argument("--name", required=True, help="Human-readable task name.")
    parser.add_argument("--mode", choices=sorted(DEFAULTS), required=True)
    parser.add_argument("--output-dir", help="Task workspace. Defaults under CODEX_HOME/state.")
    parser.add_argument("--timezone", default="Asia/Shanghai", help="IANA timezone name.")
    parser.add_argument("--start-at", default="", help="Optional local start time or note.")
    parser.add_argument("--end-at", default="", help="Optional local end time or note.")
    parser.add_argument("--feishu-doc", default="", help="Feishu wiki/docx URL or token.")
    parser.add_argument("--feishu-as", choices=("user", "bot"), default="user")
    parser.add_argument("--source", action="append", default=[], type=parse_source)
    parser.add_argument("--collector-command", default="", help="Optional deterministic collection command.")
    parser.add_argument("--normal-minutes", type=int, help="Normal patrol cadence.")
    parser.add_argument("--active-minutes", type=int, help="High-signal/live cadence.")
    parser.add_argument("--closeout-no-updates", type=int, help="No-update rounds before closeout.")
    parser.add_argument("--capture", action="store_true", help="Enable optional macOS screenshot loop.")
    parser.add_argument("--capture-interval", type=int, default=10)
    parser.add_argument("--capture-keyword", action="append", default=[])
    parser.add_argument("--force", action="store_true", help="Replace config/state in an existing directory.")
    args = parser.parse_args()

    try:
        ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        parser.error(f"unknown timezone: {args.timezone}")

    defaults = DEFAULTS[args.mode]
    normal_minutes = args.normal_minutes or defaults["normal_minutes"]
    active_minutes = args.active_minutes or defaults["active_minutes"]
    closeout_no_updates = (
        args.closeout_no_updates
        if args.closeout_no_updates is not None
        else defaults["closeout_no_updates"]
    )
    for label, value in (
        ("normal minutes", normal_minutes),
        ("active minutes", active_minutes),
        ("capture interval", args.capture_interval),
    ):
        if value < 1:
            parser.error(f"{label} must be at least 1")
    if closeout_no_updates < 0:
        parser.error("closeout no-updates threshold cannot be negative")

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    output_dir = (
        Path(args.output_dir).expanduser()
        if args.output_dir
        else codex_home / "state" / "codex-feishu-auto" / slugify(args.name)
    )
    output_dir = output_dir.resolve()
    config_path = output_dir / "config.json"
    state_path = output_dir / "state.json"
    log_path = output_dir / "duty_log.md"

    if not args.force and any(path.exists() for path in (config_path, state_path, log_path)):
        print(f"Watch already exists: {output_dir}", file=sys.stderr)
        print("Read and reuse it, or pass --force to replace its core files.", file=sys.stderr)
        return 1

    for directory in (
        output_dir,
        output_dir / "captures" / "raw_watch",
        output_dir / "captures" / "selected",
        output_dir / "logs",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).isoformat()
    config: dict[str, object] = {
        "schema_version": 1,
        "name": args.name,
        "slug": slugify(args.name),
        "mode": args.mode,
        "timezone": args.timezone,
        "workspace_dir": str(output_dir),
        "window": {"start_at": args.start_at, "end_at": args.end_at},
        "schedule": {
            "normal_minutes": normal_minutes,
            "active_minutes": active_minutes,
            "closeout_after_no_updates": closeout_no_updates,
        },
        "feishu": {
            "doc": args.feishu_doc,
            "identity": args.feishu_as,
            "read_before_write": True,
            "verify_after_write": True,
            "manual_edits_are_authoritative": True,
        },
        "sources": args.source,
        "commands": {"collect": args.collector_command},
        "capture": {
            "enabled": bool(args.capture),
            "platform": "macOS",
            "browser": "Google Chrome",
            "interval_seconds": args.capture_interval,
            "title_keywords": args.capture_keyword,
            "exact_duplicate_filter": True,
        },
        "policy": {
            "write_only_when_value_changes": True,
            "continue_on_partial_source_failure": True,
            "short_heartbeat_when_no_update": True,
            "require_user_confirmation_for_chat_alerts": True,
            "redact_secrets": True,
        },
        "created_at": created_at,
    }
    state: dict[str, object] = {
        "schema_version": 1,
        "name": args.name,
        "mode": args.mode,
        "status": "active",
        "phase": "setup",
        "seen_items": {},
        "consecutive_no_updates": 0,
        "last_run_at": "",
        "last_success_at": "",
        "last_write_revision": "",
        "next_watch": [],
        "last_errors": [],
        "closed_at": "",
        "created_at": created_at,
    }

    write_json(config_path, config)
    write_json(state_path, state)
    log_path.write_text(
        f"# {args.name} duty log\n\n"
        f"- Mode: `{args.mode}`\n"
        f"- Timezone: `{args.timezone}`\n"
        f"- Created: `{created_at}`\n\n"
        "## Checkpoints\n\n",
        encoding="utf-8",
    )
    (output_dir / ".gitignore").write_text(
        "captures/raw_watch/\nlogs/\nSTOP_CAPTURE\n", encoding="utf-8"
    )

    result = {
        "ok": True,
        "workspace": str(output_dir),
        "config": str(config_path),
        "state": str(state_path),
        "duty_log": str(log_path),
        "next": "Run render_prompt.py with the generated config.json.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
