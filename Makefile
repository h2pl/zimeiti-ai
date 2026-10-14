# Zimeiti AI —— 开发/验收入口
# 用法：make help 查看全部目标。环境：Git Bash + uv + Node(npm)。

API_DIR := apps/api
WEB_DIR := apps/web
PYTHON  ?= python

.PHONY: help install api web dev build-web verify test clean

help: ## 显示全部目标
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## 安装/同步依赖（uv sync + npm install）
	cd $(API_DIR) && uv sync
	cd $(WEB_DIR) && npm install

api: ## 启动后端 :8000（托管 apps/web/dist 构建产物；无 .env 时对话优雅降级）
	cd $(API_DIR) && uv run python serve.py --host 127.0.0.1 --port 8000

web: ## 启动前端 dev :5173（/api 代理转发到 :8000）
	cd $(WEB_DIR) && npm run dev

dev: ## 双端并行启动（Ctrl+C 一起退出；首次先跑 make install）
	$(MAKE) -j2 api web

build-web: ## 构建前端（产物在 apps/web/dist，API 直接托管该目录，无需复制）
	cd $(WEB_DIR) && npm run build

verify: ## 验收：openclaw 归零脚本 + 技能校验 + skill 测试套件
	cd $(API_DIR) && uv run --no-sync python ../scripts/verify_openclaw_removal.py
	cd apps && PYTHONUTF8=1 $(PYTHON) scripts/validate_skills.py
	cd apps && PYTHONUTF8=1 $(PYTHON) scripts/validate_skill_commands.py
	cd apps/skills/builtin/skill-wechat-publisher/tests && PYTHONUTF8=1 $(PYTHON) -m pytest -q

test: verify ## 别名

clean: ## 清理构建产物与缓存
	rm -rf $(WEB_DIR)/dist
	rm -rf $(API_DIR)/zimeiti_api.egg-info
	find $(API_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
