.PHONY: up install dev api web test check clean

# 启动 Postgres（后台）
up:
	docker compose up -d

# 安装前后端依赖
install:
	cd apps/api && uv sync --python 3.14
	cd apps/web && pnpm install

# 一键开发：Postgres + API(8000) + Web(5173)
dev:
	bash scripts/dev.sh

# 单独启动 API（热重载）
api:
	cd apps/api && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --reload

# 单独启动前端（热重载）
web:
	cd apps/web && pnpm dev

# 后端测试（自动预检 Docker/PG）
test:
	bash scripts/test-api.sh

# 后端质量门禁（ruff/mypy/bandit/coverage）
check:
	bash scripts/check-api.sh

clean:
	docker compose down
	rm -rf apps/api/.venv apps/web/node_modules
