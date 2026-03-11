#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: ./scripts/install-agent.sh <codex|claude|gemini|copilot|all> [dest] [--force]" >&2
  exit 1
fi

AGENT="$1"
shift

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python "$SCRIPT_DIR/install-agent.py" --agent "$AGENT" "$@"
