#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".env" ]; then
  set -a
  set +u
  # shellcheck disable=SC1091
  source ".env"
  set -u
  set +a
else
  echo "Warning: .env not found, continue without loading env vars."
fi

BIN_PATH="dist/main/main"
if [ ! -x "$BIN_PATH" ]; then
  echo "Error: executable not found or not executable: $BIN_PATH"
  echo "Please run script/build.sh first."
  exit 1
fi

exec "$BIN_PATH"
