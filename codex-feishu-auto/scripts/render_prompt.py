#!/usr/bin/env python3
"""Render an automation prompt from a codex-feishu-auto config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read config {path}: {exc}") from exc
    if config.get("mode") not in {"live-event", "topic-duty", "ops-check"}:
        raise SystemExit("config.mode must be live-event, topic-duty, or ops-check")
    return config


def source_lines(config: dict[str, Any]) -> str:
    sources = config.get("sources") or []
    if not sources:
        return "- No sources configured. Before scheduling, add at least one authoritative source."
    return "\n".join(
        f"- {item.get('name', 'source')}: {item.get('target', '')}" for item in sources
    )


def common_header(config: dict[str, Any], config_path: Path) -> str:
    workspace = Path(config.get("workspace_dir") or config_path.parent).expanduser().resolve()
    schedule = config.get("schedule") or {}
    window = config.get("window") or {}
    feishu = config.get("feishu") or {}
    return f"""You are the Codex monitoring agent for `{config.get('name', 'watch')}`.

Mode: `{config['mode']}`
Timezone: `{config.get('timezone', 'Asia/Shanghai')}`
Start: `{window.get('start_at') or 'from activation'}`
End: `{window.get('end_at') or 'long-running until the user stops it'}`
Normal cadence: every {schedule.get('normal_minutes', 30)} minutes
Active cadence: every {schedule.get('active_minutes', 5)} minutes
Closeout threshold: {schedule.get('closeout_after_no_updates', 3)} consecutive no-update rounds
Config: `{config_path}`
State: `{workspace / 'state.json'}`
Duty log: `{workspace / 'duty_log.md'}`
Feishu target: `{feishu.get('doc') or 'not configured; do not invent one'}`
Feishu identity: `{feishu.get('identity', 'user')}`

Configured sources:
{source_lines(config)}
"""


def common_steps(config: dict[str, Any], config_path: Path) -> str:
    workspace = Path(config.get("workspace_dir") or config_path.parent).expanduser().resolve()
    skill_dir = Path(__file__).resolve().parents[1]
    collect = (config.get("commands") or {}).get("collect") or ""
    feishu = config.get("feishu") or {}
    feishu_doc = feishu.get("doc") or ""
    collect_step = (
        f"Run the configured deterministic collector first: `{collect}`."
        if collect
        else "Collect from the configured sources with the available web, browser, API, or read-only shell tools."
    )
    current_inputs = f"`{workspace / 'state.json'}` and `{workspace / 'duty_log.md'}`"
    if feishu_doc:
        current_inputs += ", plus the current Feishu document"
        feishu_step = (
            "Write to Feishu only when there is new value. Fetch with `--api-version v2 --detail full`, "
            "write with the configured identity, then fetch again to verify revision, location, links, images, "
            "and table structure."
        )
        manual_authority_step = (
            "Treat the current Feishu document as authoritative. Never restore content a human deleted unless "
            "the user explicitly asks."
        )
    else:
        feishu_step = (
            "No Feishu target is configured. Do not invent one or attempt a document write; record the checkpoint "
            f"in `{workspace / 'duty_log.md'}` and tell the user what target is still needed."
        )
        manual_authority_step = (
            "If the user later supplies a Feishu target, fetch its current version before the first write and treat "
            "human edits as authoritative."
        )
    return f"""Every time you wake up:

1. Confirm the current local time and determine the current phase. If the end condition is met, skip normal patrol and perform closeout.
2. Read {current_inputs} before using prior conversation memory.
3. {collect_step}
4. Continue when one source fails. Report the failed route briefly, then judge using successful sources.
5. Deduplicate against `seen_items`. Label every item as official confirmation, media report, community lead, or unverified.
6. Explain why the update matters now, the usable angle or operational implication, and the missing evidence.
7. {feishu_step}
8. {manual_authority_step}
9. Update state atomically with:
   `python3 {skill_dir / 'scripts' / 'statectl.py'} record --state {workspace / 'state.json'} --new-count <N> [--seen <stable-id>] [--revision <revision>] [--next-watch <lead>]`
10. Append at most 1-3 ranking-changing judgments to `{workspace / 'duty_log.md'}`. Do not turn weak updates into a long list.
11. If there is no meaningful update, output one short heartbeat with checked sources and the next watch point.
12. Redact tokens, cookies, chat IDs, webhooks, private keys, and private server addresses from all reports.
"""


def mode_steps(config: dict[str, Any], config_path: Path) -> str:
    mode = config["mode"]
    workspace = Path(config.get("workspace_dir") or config_path.parent).expanduser().resolve()
    capture = config.get("capture") or {}
    if mode == "live-event":
        capture_text = (
            f"A separate screenshot loop is enabled at {capture.get('interval_seconds', 10)} seconds. "
            f"Inspect `{workspace / 'captures' / 'raw_watch'}` and move only useful evidence to `captures/selected`. "
            "Report raw, candidate, and used image counts separately."
            if capture.get("enabled")
            else "No screenshot loop is configured. Use official images only when they materially support the record."
        )
        return f"""Live-event rules:

- Move through setup, warmup, live, verification, and closeout phases. Increase cadence only during the high-signal live phase.
- Backtrack the latest 10-15 minutes of liveblogs or transcripts so a polling boundary does not hide an important update.
- For each meaningful update record: fact, source level, main feature or scene, one-sentence judgment, usable headline direction, and next verification point.
- {capture_text}
- Strong alerts are reserved for event start, official model/product/API/pricing/policy confirmation, or a fact that changes the editorial priority.
- When the event is over and the configured no-update threshold is reached, write a closeout with top facts, top angles, evidence gaps, and suggested next action. Then pause or delete the high-frequency automation.
"""
    if mode == "topic-duty":
        return """Topic-duty rules:

- Score new candidates for domain relevance, reader interest, writeability, timeliness, and uniqueness.
- Every recommendation must include why to write now, the angle, the content form, and the next source to verify.
- Reserve strong alerts for core company/model/product/API/pricing/open-source/policy events or a signal that changes today's publishing order.
- At the closeout time, reread the whole duty log and output an explicit TOP1 plus TOP2-3, headline direction, core thesis, article structure, missing material, and recommended publish time.
- After closeout, pause or delete the duty automation so it cannot keep producing empty patrols.
"""
    return """Operations-check rules:

- Remain read-only unless the user separately approves a repair.
- Check service health, scheduler health, output artifacts, model/provider path, production data freshness, authenticated API behavior, external sources, disk/memory, and security logs as separate facts.
- Find the live production mount or database before trusting similarly named files in a source directory.
- HTTP 200, a running container, or one successful API call is not enough to declare the whole system healthy.
- Output concise sections: verdict, evidence, anomalies, and actions. Distinguish healthy service from degraded source, auth, or fallback path.
- Long-running checks do not close merely because there is no change; they record a compact healthy checkpoint and wait for the next scheduled run.
"""


def render(config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    schedule = config.get("schedule") or {}
    prompt = "\n".join(
        (common_header(config, config_path), common_steps(config, config_path), mode_steps(config, config_path))
    ).strip()
    return {
        "name": config.get("name", "watch"),
        "mode": config["mode"],
        "recommended_schedule": {
            "normal_minutes": schedule.get("normal_minutes", 30),
            "active_minutes": schedule.get("active_minutes", 5),
            "strategy": "Use one heartbeat for interactive event/duty work; use local or server cron for stable recurring checks.",
        },
        "prompt": prompt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Codex automation prompt.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--format", choices=("json", "markdown", "prompt"), default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    payload = render(read_config(config_path), config_path)
    if args.format == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    elif args.format == "prompt":
        text = payload["prompt"] + "\n"
    else:
        schedule = payload["recommended_schedule"]
        text = (
            f"# {payload['name']} automation prompt\n\n"
            f"- Mode: `{payload['mode']}`\n"
            f"- Normal cadence: `{schedule['normal_minutes']} minutes`\n"
            f"- Active cadence: `{schedule['active_minutes']} minutes`\n\n"
            "## Prompt\n\n"
            f"{payload['prompt']}\n"
        )
    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(output_path.resolve())}, ensure_ascii=False))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
