## Why

全新项目（起点分支 `zimeiti-init` 无代码）。按 `docs/prd/zimeiti-ai-prd.md`：阶段一先复制实现 Easel，且后端最终要与 OpenClaw 解耦、改用 deepagents 实现。

本变更是阶段一的后半部：**把 Easel 后端复制过来并跑起来**，同时登记其中依赖 OpenClaw 的模块，作为后续"去 OpenClaw、改用 deepagents"变更的输入。前端复制由独立变更 `phase1-easel-web-copy` 承担。

## What Changes

- 新建 `apps/api`：整份复制 Easel 后端 `easel/` 包与 `web/app.py`
- 复制后端依赖配置（`pyproject.toml` / `requirements`）
- 安装依赖并启动服务，确认 `/api/status` 有响应
- 登记依赖 OpenClaw 的模块清单（`openclaw_cmd.py`、`openclaw_workspace.py`、`gateway_endpoint.py`、`gateway_questions.py`、`local_agents.py`、`commands/*` 等）

## Capabilities

### New Capabilities

- `easel-api-copy`: 以 Easel 后端源码为起点的 API 工程——源码复制完整、依赖就绪、服务可启动，并输出 OpenClaw 依赖清单

### Modified Capabilities

（无。全新项目，无既有能力规格。）

## Impact

- 新增 `apps/api/`（`easel/`、`app.py`、依赖配置）
- 本地后端启动方式改为 `apps/api` 下的 API 服务
- 本变更不移除 OpenClaw 依赖，只登记；解耦归后续变更
