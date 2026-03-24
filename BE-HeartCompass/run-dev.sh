#!/bin/bash
set -e

ROLE="${1:-http}"

if [ "$ROLE" = "http" ]; then
    # uv run robyn -m main --dev    # robyn热重载异常，不断重启
    uv run hupper -m main
elif [ "$ROLE" = "lark" ]; then
    uv run hupper -m lark_main
else
    echo "Usage: $0 [http|lark]"
    exit 1
fi
