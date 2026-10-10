export PYTHONUTF8 := 1
export PYTHONIOENCODING := utf-8

.PHONY: up install dev api web test check clean ops-daily hosted-daily schedule-install

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
	cd apps/api && uv run python -m zimeiti_api.operations.daily

# 每日内容任务：触发托管循环（选题→创作→中断等审批）
hosted-daily:
	cd apps/api && uv run python -m zimeiti_api.runtime.hosted_daily

# 注册/更新 Windows 计划任务（x2：07:30 托管内容触发 / 08:30 运营取数；
# 仅用户登录时运行——xhs 取数与浏览器操作需真实窗口）
schedule-install:
	cmd //c "schtasks /Create /F /TN \"zimeiti-ai-hosted-daily\" /SC DAILY /ST 07:30 /TR \"E:\\Projects\\zimeiti-ai\\scripts\\run_hosted_daily.bat\""
	cmd //c "schtasks /Create /F /TN \"zimeiti-ai-ops-daily\" /SC DAILY /ST 08:30 /TR \"E:\\Projects\\zimeiti-ai\\scripts\\run_ops_daily.bat\""

# 常驻网关（托管主形态）：审批 API + 进程内调度器（07:30 内容/08:30 取数），一条命令无人值守
gateway:
	cd apps/api && .venv/Scripts/python.exe -m zimeiti_api.runtime.gateway
