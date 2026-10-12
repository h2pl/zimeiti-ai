---
change: phase1-easel-api-copy
design-doc: docs/openspec/changes/phase1-easel-api-copy/design.md
base-ref: 7261f21ac1c1b0f0e3a34b0bc2e5b45d3361a00f
---

<!-- comet-task-authority: docs/openspec/changes/phase1-easel-api-copy/tasks.md -->

# 实施计划：复制 Easel 后端并跑起来

配置：autonomous / direct / standard。范围仅为复制与启动验证，不改写复制来的代码。

## 任务 1：复制后端源码与配置

<!-- comet-task-ref:65e2be98-bbc9-4a5c-8beb-f5c85d1d2c4d -->
复制 `Easel/easel` → `apps/api/easel`；`Easel/web/app.py` → `apps/api/app.py`

<!-- comet-task-ref:bcf52849-47e6-41d2-881c-ad3c1c5ca70d -->
复制 `pyproject.toml`、`pytest.ini` → `apps/api`；补齐 app.py 依赖的仓库根布局（`apps/scripts` 共享脚本、`apps/outputs`、`apps/profiles`、`apps/skills`）

<!-- comet-task-ref:03a1d2af-454f-4388-ac33-6fb0f8ef806a -->
验收：文件与 Easel 逐行一致，包目录无遗漏（15 个 easel 模块 + 4419 行 app.py）

## 任务 2：装依赖并跑起来

<!-- comet-task-ref:20b6208f-69c4-42e8-a771-8770399d564d -->
`uv venv --python 3.12` + 安装核心依赖（fastapi/uvicorn/sse-starlette/httpx/pydantic/python-multipart/markdown/segno/websocket-client/cryptography；媒体类重依赖按需后补）

<!-- comet-task-ref:6b69826e-57be-4534-a174-f485623810f0 -->
启动 `uvicorn app:app --port 8000`

<!-- comet-task-ref:92769b0c-8cd5-447c-9ee8-bcc00f7db679 -->
验收：`/api/status` 返回 200（`{"gateway":true,"skills":[],"personas":[]}`），无致命启动报错

## 任务 3：登记 OpenClaw 依赖清单

<!-- comet-task-ref:1baf9c7f-2ed1-4a21-8e02-10e4f6ff3b1f -->
梳理 9 个依赖 OpenClaw 的模块（openclaw_cmd/openclaw_workspace/gateway_endpoint/gateway_questions/local_agents/commands/*）写入 openclaw-dependencies.md

<!-- comet-task-ref:679ef89c-5390-43a5-93a2-9fc7cb98bc9c -->
验收：清单覆盖全部 `import openclaw` 或调用 OpenClaw 命令的文件

## 风险与回滚

- OpenClaw 缺失：依赖网关的端点不可用（返回错误/空态）——解耦变更补齐
- Python 3.14 部分重依赖（opencv/librosa/whisper）可能无 wheel → 锁 3.12；媒体功能按需后补
- 回滚：分支隔离，丢弃分支即回到 `h2pl/zimeiti-ai`
