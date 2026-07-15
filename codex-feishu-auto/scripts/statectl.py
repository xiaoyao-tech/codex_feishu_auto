#!/usr/bin/env python3
"""Atomically inspect and update codex-feishu-auto state files."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read state {path}: {exc}") from exc
    if not isinstance(state, dict):
        raise SystemExit("state root must be an object")
    state.setdefault("seen_items", {})
    state.setdefault("consecutive_no_updates", 0)
    state.setdefault("next_watch", [])
    state.setdefault("last_errors", [])
    return state


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def print_state(state: dict[str, Any]) -> None:
    print(json.dumps(state, ensure_ascii=False, indent=2))


def record(args: argparse.Namespace) -> int:
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    timestamp = args.now or now_iso()
    seen = state.setdefault("seen_items", {})
    if not isinstance(seen, dict):
        seen = {}
        state["seen_items"] = seen
    for item in args.seen:
        seen[item] = timestamp
    if len(seen) > args.max_seen:
        ordered = sorted(seen.items(), key=lambda pair: pair[1], reverse=True)[: args.max_seen]
        state["seen_items"] = dict(ordered)

    state["last_run_at"] = timestamp
    if args.new_count > 0:
        state["consecutive_no_updates"] = 0
        state["last_success_at"] = timestamp
    else:
        state["consecutive_no_updates"] = int(state.get("consecutive_no_updates", 0)) + 1
    if args.phase:
        state["phase"] = args.phase
    if args.revision is not None:
        state["last_write_revision"] = args.revision
    if args.next_watch:
        state["next_watch"] = args.next_watch
    state["last_errors"] = args.error
    atomic_write(path, state)
    print_state(state)
    return 0


def set_phase(args: argparse.Namespace) -> int:
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    state["phase"] = args.phase
    state["last_run_at"] = args.now or now_iso()
    atomic_write(path, state)
    print_state(state)
    return 0


def should_close(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state).expanduser().resolve())
    count = int(state.get("consecutive_no_updates", 0))
    closed = state.get("status") == "closed"
    result = {
        "should_close": closed or (args.threshold > 0 and count >= args.threshold),
        "status": state.get("status", "active"),
        "consecutive_no_updates": count,
        "threshold": args.threshold,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def close(args: argparse.Namespace) -> int:
    path = Path(args.state).expanduser().resolve()
    state = load_state(path)
    timestamp = args.now or now_iso()
    state["status"] = "closed"
    state["phase"] = "closed"
    state["closed_at"] = timestamp
    state["last_run_at"] = timestamp
    atomic_write(path, state)
    print_state(state)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or update a monitoring state file.")
    sub = parser.add_subparsers(dest="command", required=True)

    show_parser = sub.add_parser("show")
    show_parser.add_argument("--state", required=True)
    show_parser.set_defaults(func=lambda args: (print_state(load_state(Path(args.state).expanduser().resolve())) or 0))

    record_parser = sub.add_parser("record")
    record_parser.add_argument("--state", required=True)
    record_parser.add_argument("--new-count", type=int, required=True)
    record_parser.add_argument("--seen", action="append", default=[])
    record_parser.add_argument("--phase")
    record_parser.add_argument("--revision")
    record_parser.add_argument("--next-watch", action="append", default=[])
    record_parser.add_argument("--error", action="append", default=[])
    record_parser.add_argument("--max-seen", type=int, default=5000)
    record_parser.add_argument("--now", help="Override timestamp for deterministic tests.")
    record_parser.set_defaults(func=record)

    phase_parser = sub.add_parser("set-phase")
    phase_parser.add_argument("--state", required=True)
    phase_parser.add_argument("--phase", required=True)
    phase_parser.add_argument("--now")
    phase_parser.set_defaults(func=set_phase)

    close_check = sub.add_parser("should-close")
    close_check.add_argument("--state", required=True)
    close_check.add_argument("--threshold", type=int, default=3)
    close_check.set_defaults(func=should_close)

    close_parser = sub.add_parser("close")
    close_parser.add_argument("--state", required=True)
    close_parser.add_argument("--now")
    close_parser.set_defaults(func=close)

    args = parser.parse_args()
    if getattr(args, "new_count", 0) < 0:
        parser.error("--new-count cannot be negative")
    if getattr(args, "threshold", 0) < 0:
        parser.error("--threshold cannot be negative")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
