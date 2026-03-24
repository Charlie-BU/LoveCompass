#!/bin/bash
set -e

ROLE="${1:-http}"

if [ "$ROLE" = "http" ]; then
    uv run robyn -m main --process=1 --workers=3  # 切不可开多进程，否则会导致一个耗时请求无法正确处理 why??
elif [ "$ROLE" = "lark" ]; then
    uv run -m lark_main
else
    echo "Usage: $0 [http|lark]"
    exit 1
fi
