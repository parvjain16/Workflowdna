#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  echo "Install dependencies first: bash scripts/setup.sh"
  exit 1
fi
cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
# The frontend proxies /api to this backend. Credentials never enter the browser.
echo "WorkflowDNA: http://127.0.0.1:3000"
echo "Press Ctrl+C to stop both servers."
npm --prefix frontend run dev -- --port 3000
