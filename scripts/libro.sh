#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: ./scripts/libro.sh <install|doctor|remove|audit|scan|report> [args...]" >&2
  exit 1
fi

COMMAND="$1"
shift

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python "$SCRIPT_DIR/libro.py" "$COMMAND" "$@"
