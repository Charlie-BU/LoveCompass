#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if command -v uv >/dev/null 2>&1; then
  echo "[pack-all] Found uv, installing and running PyInstaller via uv..."
  uv add pyinstaller
  uv run pyinstaller --onedir src/main.py
else
  echo "[pack-all] uv not found, fallback to pip..."
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "[pack-all] Error: python not found in PATH."
    exit 1
  fi

  "$PYTHON_BIN" -m pip install pyinstaller
  pyinstaller --onedir src/main.py
fi
