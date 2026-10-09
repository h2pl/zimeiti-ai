#!/usr/bin/env bash
# 一键预检 + 跑后端测试：Docker 未起自动拉起，PG 未就绪自动等待。
set -e
cd "$(dirname "$0")/.."
docker compose up -d
cd apps/api
exec .venv/Scripts/python.exe -m pytest tests/ -q
