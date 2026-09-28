#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if command -v uv >/dev/null 2>&1; then
  [[ -x .venv/bin/python ]] || uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -r requirements.txt
else
  [[ -x .venv/bin/python ]] || python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
npm --prefix frontend ci
if [[ ! -f .env ]]; then cp .env.example .env; fi
echo "Dependencies installed. Configure RIVER_API_KEY in .env, then bash scripts/start.sh."
