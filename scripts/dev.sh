#!/usr/bin/env bash
# 一键开发环境：Postgres + API + Web（Ctrl+C 全部退出）
set -e
cd "$(dirname "$0")/.."

docker compose up -d

cleanup() {
  echo "正在停止服务..."
  kill 0 2>/dev/null
}
trap cleanup EXIT

echo "== API: http://localhost:8000 =="
(cd apps/api && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --reload) &

echo "== Web: http://localhost:5173 =="
(cd apps/web && pnpm dev) &

wait
