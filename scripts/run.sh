#!/usr/bin/env bash
# Launcher for hermes_cmd.py — handles cwd + venv detection.
# Works from any directory, both on Mac (.venv) and VPS (venv).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if [[ -x ".venv/bin/python" ]]; then
    PY=".venv/bin/python"
elif [[ -x "venv/bin/python" ]]; then
    PY="venv/bin/python"
else
    echo '{"error":"No venv found at .venv/ or venv/. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"}' >&2
    exit 1
fi

exec "$PY" scripts/hermes_cmd.py "$@"
