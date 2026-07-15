#!/usr/bin/env zsh
set -euo pipefail

OUTPUT_DIR="${WATCH_OUTPUT_DIR:-./captures}"
INTERVAL="${WATCH_CAPTURE_INTERVAL:-10}"
KEYWORDS="${WATCH_TITLE_KEYWORDS:-youtube,liveblog}"
ONCE=0
CHECK_ONLY=0
DEDUPE=1
BROWSER="Google Chrome"

usage() {
  cat <<'EOF'
Capture the active Google Chrome window on macOS when its tab title matches.

Usage:
  capture_watch.sh [options]

Options:
  --output-dir PATH   Base directory. Raw images go to PATH/raw_watch.
  --interval SECONDS  Capture interval, default 10.
  --keywords CSV      Case-insensitive active-tab title keywords.
  --once              Try one capture and exit.
  --no-dedupe         Keep exact duplicate frames.
  --check             Check platform and commands without taking a screenshot.
  -h, --help          Show this help.

Stop a running loop by creating OUTPUT_DIR/STOP_CAPTURE.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      [[ $# -ge 2 ]] || { echo "--output-dir needs a path" >&2; exit 2; }
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --interval)
      [[ $# -ge 2 ]] || { echo "--interval needs seconds" >&2; exit 2; }
      INTERVAL="$2"
      shift 2
      ;;
    --keywords)
      [[ $# -ge 2 ]] || { echo "--keywords needs comma-separated values" >&2; exit 2; }
      KEYWORDS="$2"
      shift 2
      ;;
    --once)
      ONCE=1
      shift
      ;;
    --no-dedupe)
      DEDUPE=0
      shift
      ;;
    --check)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "capture_watch.sh requires macOS." >&2
  exit 1
fi
if ! [[ "$INTERVAL" =~ '^[0-9]+$' ]] || (( INTERVAL < 1 )); then
  echo "--interval must be a positive integer." >&2
  exit 2
fi

required=(osascript screencapture swift shasum)
missing=()
for command_name in $required; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    missing+=("$command_name")
  fi
done
if (( ${#missing[@]} > 0 )); then
  echo "Missing commands: ${missing[*]}" >&2
  exit 1
fi
if (( CHECK_ONLY )); then
  echo "Capture dependencies found. Grant Screen Recording permission to the terminal/Codex app before the first run."
  exit 0
fi

RAW_DIR="$OUTPUT_DIR/raw_watch"
LOG_FILE="$OUTPUT_DIR/capture_watch.log"
STOP_FILE="$OUTPUT_DIR/STOP_CAPTURE"
mkdir -p "$RAW_DIR"
rm -f "$STOP_FILE"
LAST_HASH=""

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$1" >> "$LOG_FILE"
}

title_matches() {
  local title_lc keyword keyword_lc
  title_lc="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  for keyword in ${(s:,:)KEYWORDS}; do
    keyword_lc="$(printf '%s' "$keyword" | tr '[:upper:]' '[:lower:]' | xargs)"
    [[ -n "$keyword_lc" && "$title_lc" == *"$keyword_lc"* ]] && return 0
  done
  return 1
}

find_window_id() {
  swift -e '
    import CoreGraphics
    import Foundation
    let owner = CommandLine.arguments.dropFirst().first ?? "Google Chrome"
    let options = CGWindowListOption(arrayLiteral: .optionAll, .excludeDesktopElements)
    let windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as NSArray? as? [[String: Any]] ?? []
    var bestNumber: Int? = nil
    var bestArea = 0
    for window in windows {
      guard (window[kCGWindowOwnerName as String] as? String) == owner else { continue }
      guard let bounds = window[kCGWindowBounds as String] as? [String: Any],
            let width = bounds["Width"] as? Int,
            let height = bounds["Height"] as? Int else { continue }
      let area = width * height
      if area > bestArea, let number = window[kCGWindowNumber as String] as? Int {
        bestArea = area
        bestNumber = number
      }
    }
    if let number = bestNumber { print(number) }
  ' "$BROWSER" 2>/dev/null | tr -d '\n'
}

capture_once() {
  local title window_id timestamp output hash bytes
  title="$(osascript -e 'tell application "Google Chrome" to if (count of windows) > 0 then get title of active tab of front window' 2>/dev/null || true)"
  if [[ -z "$title" ]]; then
    log "skip no-active-chrome-window"
    return 0
  fi
  if ! title_matches "$title"; then
    log "skip title-not-matched title=${title}"
    return 0
  fi
  window_id="$(find_window_id)"
  if [[ -z "$window_id" ]]; then
    log "failed chrome-window-id title=${title}"
    return 1
  fi
  timestamp="$(date '+%Y-%m-%d_%H%M%S')"
  output="$RAW_DIR/${timestamp}_chrome_window.png"
  if ! screencapture -x -l "$window_id" "$output"; then
    log "failed screenshot window_id=${window_id} title=${title}"
    return 1
  fi
  hash="$(shasum -a 256 "$output" | awk '{print $1}')"
  if (( DEDUPE )) && [[ -n "$LAST_HASH" && "$hash" == "$LAST_HASH" ]]; then
    rm -f "$output"
    log "skip exact-duplicate title=${title}"
    return 0
  fi
  LAST_HASH="$hash"
  bytes="$(stat -f%z "$output" 2>/dev/null || echo 0)"
  log "captured path=${output} window_id=${window_id} bytes=${bytes} title=${title}"
  print -r -- "$output"
}

log "start interval=${INTERVAL}s keywords=${KEYWORDS} raw_dir=${RAW_DIR}"
if (( ONCE )); then
  capture_once
  exit $?
fi

while true; do
  if [[ -f "$STOP_FILE" ]]; then
    log "stop-file-detected"
    exit 0
  fi
  capture_once || true
  sleep "$INTERVAL"
done
