#!/usr/bin/env sh
set -eu

if [ "$#" -lt 2 ]; then
  echo "Usage: ./scripts/libro.sh <install|doctor|remove> <codex|claude|gemini|copilot|all> [options]" >&2
  exit 1
fi

COMMAND="$1"
AGENT="$2"
shift 2

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python "$SCRIPT_DIR/libro.py" "$COMMAND" "$AGENT" "$@"
