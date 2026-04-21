#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

ROLE="${1:-lark}"

if [ "$ROLE" = "http" ]; then
    # uv run robyn -m main --dev    # robyn热重载异常，不断重启
    uv run hupper -m src.robyn_main
elif [ "$ROLE" = "lark" ]; then
    uv run hupper -m src.lark_main
else
    echo "Usage: $0 [http|lark]"
    exit 1
fi
