#!/usr/bin/env bash
# 后端质量门禁一键检查：format → lint → types → security → tests+coverage
set -e
cd "$(dirname "$0")/../apps/api"

echo "== 1/5 ruff format =="
.venv/Scripts/python.exe -m ruff format src tests

echo "== 2/5 ruff lint =="
.venv/Scripts/python.exe -m ruff check src tests

echo "== 3/5 mypy =="
.venv/Scripts/python.exe -m mypy src/zimeiti_api

echo "== 4/5 bandit =="
.venv/Scripts/python.exe -m bandit -q -r src/zimeiti_api

echo "== 5/5 pytest + coverage(>=80%) =="
.venv/Scripts/python.exe -m pytest tests/ -q --cov=zimeiti_api --cov-report=term --cov-fail-under=80

echo "== 全部门禁通过 =="
