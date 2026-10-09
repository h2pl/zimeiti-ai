#!/usr/bin/env bash
# dev env: Postgres + API + Web (Ctrl+C to stop)
set -e
cd "$(dirname "$0")/.."

docker compose up -d

cleanup() {
  echo "stopping services..."
  kill 0 2>/dev/null
}
trap cleanup EXIT

echo "== API: http://localhost:8000 =="
(cd apps/api && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --reload) &

echo "== Web: http://localhost:5173 =="
(cd apps/web && pnpm dev) &

wait
