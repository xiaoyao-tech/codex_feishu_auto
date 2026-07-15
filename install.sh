#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$REPO_DIR/codex-feishu-auto"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
TARGET_DIR="$CODEX_ROOT/skills/codex-feishu-auto"
FORCE=0

usage() {
  cat <<'EOF'
Install codex-feishu-auto into a Codex skills directory.

Usage:
  ./install.sh [--target PATH] [--force]

Options:
  --target PATH  Install to an explicit directory.
  --force        Replace an existing installation.
  -h, --help     Show this help.

Environment:
  CODEX_HOME     Defaults to $HOME/.codex.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || { echo "--target needs a path" >&2; exit 2; }
      TARGET_DIR="$2"
      shift 2
      ;;
    --force)
      FORCE=1
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

TARGET_DIR="$(python3 -c 'import os, sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$TARGET_DIR")"
case "$TARGET_DIR" in
  ""|"/"|"$HOME"|"$CODEX_ROOT")
    echo "Refusing unsafe install target: $TARGET_DIR" >&2
    exit 2
    ;;
esac

[[ -f "$SOURCE_DIR/SKILL.md" ]] || {
  echo "Skill source not found: $SOURCE_DIR" >&2
  exit 1
}

if [[ -e "$TARGET_DIR" && "$FORCE" -ne 1 ]]; then
  echo "Target already exists: $TARGET_DIR" >&2
  echo "Re-run with --force to replace it." >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET_DIR")"
TMP_DIR="${TARGET_DIR}.tmp.$$"
rm -rf "$TMP_DIR"
cp -R "$SOURCE_DIR" "$TMP_DIR"
find "$TMP_DIR" -name '.DS_Store' -delete
find "$TMP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
chmod +x "$TMP_DIR"/scripts/*.py "$TMP_DIR"/scripts/*.sh

if [[ -e "$TARGET_DIR" ]]; then
  rm -rf "$TARGET_DIR"
fi
mv "$TMP_DIR" "$TARGET_DIR"

echo "Installed codex-feishu-auto to: $TARGET_DIR"
echo "Restart Codex if the skill does not appear immediately."
echo "Next: python3 '$TARGET_DIR/scripts/doctor.py'"
