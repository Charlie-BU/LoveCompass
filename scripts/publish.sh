#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ $# -ne 1 ]; then
  echo "Usage: bash scripts/release-tag.sh <version>"
  echo "Example:"
  echo "  bash scripts/release-tag.sh 1.2.3"
  echo "  bash scripts/release-tag.sh v1.2.3"
  exit 1
fi

INPUT_VERSION="$1"
if [[ "$INPUT_VERSION" == v* ]]; then
  TAG="$INPUT_VERSION"
else
  TAG="v$INPUT_VERSION"
fi

echo "Preparing release with tag: $TAG"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "Switching branch: $CURRENT_BRANCH -> main"
  git switch main
fi

echo "Pulling latest main from origin..."
git pull --ff-only origin main

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "Tag already exists locally: $TAG"
  exit 1
fi

echo "Cleaning previous build artifacts..."
rm -rf dist

echo "Building package with uv..."
uv build

echo "Validating distributions with twine..."
uvx twine check dist/*

echo "Creating tag: $TAG"
git tag "$TAG"

echo "Pushing tag to origin: $TAG"
git push origin "$TAG"

echo "Done. GitHub Actions should now trigger the PyPI publish workflow."
