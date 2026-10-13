## Why

需求来源：`docs/prd/zimeiti-ai-prd.md` 阶段一——复制 Easel 后必须"与 OpenClaw 解耦、改用 deepagents"。当前 `apps/api` 已复制 Easel 后端（`phase1-easel-api-copy`），但对话流式、问答题链路依赖 OpenClaw 网关（本环境无 OpenClaw 可执行文件，端点不可用）。

本变更用 deepagents（LangGraph）实现进程内运行时，替换 OpenClaw 依赖，让对话链路真正可用。

## What Changes

- 新增 `apps/api/easel/agent_runtime.py`：deepagents 进程内运行时——会话历史落盘、`create_deep_agent` + `ask_human` HITL 中断、按 Easel SSE 契约发帧（token/thinking/activity/question/error/done）
- `app.py` 三个接缝：`/api/chat/stream` 顶部按 `ZIMEITI_RUNTIME` 分支到运行时（默认 deepagents，openclaw 路径保留可切回）；`/api/chat/question/answer`、`/api/chat/question/status` 在运行时模式下走运行时存储
- 模型经环境变量配置（`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `ZIMEITI_MODEL`）；未配置时返回明确错误帧而非崩溃
- 原 OpenClaw 路径代码保留不删（切换开关），供回退与对照

## Capabilities

### New Capabilities

- `deepagents-runtime`: deepagents 进程内运行时承载对话链路——流式对话可用、HITL 问题卡内联且可恢复、无模型时优雅降级、SSE 契约与 Easel 前端兼容

### Modified Capabilities

（无既有规格变更；easel-api-copy 规格仍成立——服务可启动、复制保真不受影响。）

## Impact

- `apps/api/easel/agent_runtime.py`（新增）、`app.py`（三处接缝）、`apps/sessions/`（运行时数据目录）
- 新增依赖：langchain-openai（deepagents 已带入 langchain-core/langgraph）
- OpenClaw 模块文件保留但主链路不再调用；解耦完成后可评估删除
