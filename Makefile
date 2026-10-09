export PYTHONUTF8 := 1
export PYTHONIOENCODING := utf-8

.PHONY: up install dev api web test check clean

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
	cd apps/api && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --reload

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
