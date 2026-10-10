export PYTHONUTF8 := 1
export PYTHONIOENCODING := utf-8

.PHONY: up install dev api web test check clean ops-daily

# start Postgres (background)
up:
	docker compose up -d

# install deps for api & web
install:
	cd apps/api && uv sync
	cd apps/web && pnpm install

# one-command dev: Postgres + API(8000) + Web(5173)
dev:
	bash scripts/dev.sh

# run API only (hot reload)
api:
	cd apps/api && .venv/Scripts/python.exe -m uvicorn zimeiti_api.app:app --port 8000 --reload

# run web only (hot reload)
web:
	cd apps/web && pnpm dev

# backend tests (auto preflight docker/pg)
test:
	bash scripts/test-api.sh

# quality gates: ruff/mypy/bandit/coverage
check:
	bash scripts/check-api.sh

clean:
	docker compose down
	rm -rf apps/api/.venv apps/web/node_modules

# 每日运营任务：取数(T-1) → 按量校准（计划任务/手动同一入口）
ops-daily:
	cd apps/api && uv run python -m zimeiti_api.ops_daily

# 注册/更新 Windows 计划任务（每天 08:30，仅用户登录时运行——xhs 取数需真实浏览器窗口）
schedule-install:
	cmd //c "schtasks /Create /F /TN \"zimeiti-ai-ops-daily\" /SC DAILY /ST 08:30 /TR \"E:\\Projects\\zimeiti-ai\\scripts\\run_ops_daily.bat\""
