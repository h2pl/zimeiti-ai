#!/usr/bin/env bash
# dev env: Postgres + API + Web (Ctrl+C to stop)
set -e
cd "$(dirname "$0")/.."

docker compose up -d

APIS_PID=""
WEBS_PID=""
cleanup() {
  echo "stopping services..."
  [ -n "$APIS_PID" ] && kill "$APIS_PID" 2>/dev/null
  [ -n "$WEBS_PID" ] && kill "$WEBS_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

echo "== API: http://localhost:8000 =="
(cd apps/api && .venv/Scripts/python.exe -m uvicorn zimeiti_api.app:app --port 8000 --reload) &
APIS_PID=$!

echo "== Web: http://localhost:5173 =="
(cd apps/web && pnpm dev) &
WEBS_PID=$!

wait
