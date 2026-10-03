#!/usr/bin/env bash
# One-click launcher: installs what's needed, builds the UI, starts Vectron, opens the browser.
set -e
cd "$(dirname "$0")/backend"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install it with:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "then open a new terminal and run this again."
  read -r -p "Press Enter to close." _
  exit 1
fi
uv sync --quiet
uv run vectron start
