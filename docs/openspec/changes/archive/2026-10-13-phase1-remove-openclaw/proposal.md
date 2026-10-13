# 提案：phase1-remove-openclaw

## Why

`phase1-deepagents-runtime` 只把流式对话入口（`/api/chat/stream`）切到 deepagents，且显式保留 `ZIMEITI_RUNTIME=openclaw` 兜底——需求「OpenClaw 全部移除，改用 deepagents」未闭环：非流式入口（`/api/chat`、`/api/skill`、画像 AI 增强）仍经 `openclaw agent` CLI 执行，设置面板仍读写 `openclaw.json`，网关探活/会话自愈/跨进程锁等死代码原样留存，Easel 复制来的 OpenClaw 控制 CLI（`easel.cli`、`commands/`）与 5 个 openclaw 专用模块全部在库。此外 `pyproject.toml` 从未声明 `deepagents` 依赖（旧 venv 手工安装），`uv sync` 重建环境即断——本轮验收时实际暴露。

## What Changes

- **BREAKING** 移除 `ZIMEITI_RUNTIME=openclaw` 兜底与 OpenClaw HTTP 网关/CLI 双路径：deepagents 是唯一 agent 执行路径；`/api/chat`、`/api/skill`、画像 AI 增强改走 `_agent_runtime.ask/ask_sync`
- 移除 openclaw 专用模块：`easel/{gateway_endpoint,gateway_questions,openclaw_cmd,openclaw_workspace,local_agents,cli,__main__}.py` 与 `easel/commands/`；移除 `easel` 控制台入口及仅问答题桥接使用的 `websocket-client`/`cryptography` 依赖
- 移除死代码：`run_agent_sync`、`check_gateway`、`clean_agent_output`、`_heal_openclaw_session`、`_resolve_transport`/`_pin_transport`、`_CrossProcLock`、`_GatewayHttpProc`、`_sync_openclaw_chat`、`_openclaw_provider_creds`、问答题 gateway 分支等
- 设置面板去 openclaw.json 化：模型配置仅经 `.env`（`OPENAI_*` 等槽位）；`/api/session/{key}` 删除改为操作 deepagents 会话文件；`/api/settings/local-agents` 端点移除
- 技能目录归位：`skills/openclaw/`（Easel 复制期把单技能内容平铺进组目录，`WECHAT_SKILL_DIR` 等路径自复制起即断）→ `skills/builtin/skill-wechat-publisher/`；`validate_skills.py` 修正并移除本仓从未随迁技能的契约条目
- 依赖修复：声明 `deepagents`/`langchain-core`；`requires-python` 收紧 ≥3.11；`biliup` 钉 1.2.9（最后带 cp39-abi3 win_amd64 wheel 的版本，1.2.11 仅 sdist 且本机无 Rust 工具链）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `deepagents-runtime`：对话链路唯一化（移除 openclaw 兜底，非流式入口纳入运行时）；新增「模型与会话管理不依赖 OpenClaw」要求。详见 `specs/deepagents-runtime/spec.md`。

## Impact

- **代码**：`apps/api/app.py`（约 -700 行）、`apps/api/easel/agent_runtime.py`（补 `OPENAI_MODEL` 槽位读取与 `AIMessageChunk` 顶层导入）、`apps/scripts/validate_skills.py`
- **删除**：`apps/api/easel/` 下 7 个模块 + `commands/` 子包、`apps/scripts/gateway.{sh,ps1}`
- **目录**：`apps/skills/openclaw/` → `apps/skills/builtin/skill-wechat-publisher/`
- **API 行为**：`/api/chat`、`/api/skill`、`/api/settings/models*`、`/api/session/{key}` 变更；`/api/settings/local-agents` 移除（64 路由，较此前 66 少 2）
- **依赖**：`pyproject.toml` 如上；环境前置：需 Python ≥3.11
