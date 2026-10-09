# Zimeiti AI

Your AI 自媒体人——社媒内容创作与获客 agent。

## 结构（单仓库四目录）

- `apps/api` — 后端：FastAPI + deepagents agent 运行时（选题→创作→发布最小闭环）
- `apps/web` — 前端：Next.js 工作台/审批界面
- `packages/skills` — 技能包（SKILL.md + scripts）
- `mcp/` — MCP servers（媒体处理/发布/搜索/数据采集）

## 开发

```bash
docker compose up -d          # Postgres + pgvector
cd apps/api && uv sync        # 后端环境（Python 3.12）
uv run uvicorn zimeiti_api.app:app --port 8000 --reload
cd apps/web && pnpm install && pnpm dev
```

需求与设计文档：`docs/prd/`、`docs/superpowers/plans/`、`openspec/changes/mvp-scaffold/`
