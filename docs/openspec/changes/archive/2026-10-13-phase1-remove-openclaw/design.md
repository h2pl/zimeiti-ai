---
comet_change: phase1-remove-openclaw
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-13-phase1-remove-openclaw
status: final
---

# 设计：phase1-remove-openclaw

## 背景与目标

`phase1-deepagents-runtime` 交付后，OpenClaw 相关代码仍大量残留（兜底开关、非流式 CLI 路径、网关探活/会话自愈/跨进程锁、openclaw.json 配置面、Easel 控制 CLI、skills/openclaw 目录）。本变更把「deepagents 是唯一 agent 执行路径」贯彻到底，并修复验收时暴露的依赖声明缺陷。

## 高层决策

### D1 对话执行唯一化

- 流式 `/api/chat/stream`：删除 `if runtime_enabled()` 分支与 openclaw 兜底体（约 475 行），无条件走 `_agent_runtime.run_turn`；`runtime_enabled()` 保留为常真兼容口（`ZIMEITI_RUNTIME=openclaw` 不再产生任何分支差异）。
- 非流式入口：`/api/chat` → `await _agent_runtime.ask(sk, message)`；`/api/skill` → 同上；画像 AI 增强（线程池同步上下文）→ `_agent_runtime.ask_sync`（内部 `asyncio.run(ask(...))`）。三者与流式共享同一会话历史（sessions/<key>.json + LangGraph checkpoint）。
- 删除仅服务 openclaw 双路径的基础设施：`_resolve_transport`/`_pin_transport`（传输层钉扎）、`_GatewayHttpProc`（HTTP 伪进程）、`_CrossProcLock`（fcntl/msvcrt 跨进程会话锁）、`_heal_openclaw_session`（thinking 块自愈）、`_openclaw_session_id`（uuid5 transcript 钉扎）、问答题 gateway WS 桥接分支。

### D2 模型配置：仅经 .env

- `easel/agent_runtime.py::_build_model` 读取 `OPENAI_MODEL`（兜底 `ZIMEITI_MODEL`），与设置面板 openai 槽位的写入键对齐。
- 设置面板保存端点重写：仅 `.env` 槽位键（openai/relay/anthropic/siliconflow），删除 `openclaw.json` 同步（`_sync_openclaw_chat`/`_sync_anthropic_provider`/`_openclaw_provider_creds`/`_set_openclaw_primary`/`_declare_anthropic_provider`）、custom 供应商与 primary 语义。
- GET `_model_channels`：`primary` 由 `OPENAI_MODEL` 推导（`openai/<model>`），不再读 openclaw.json；chat 行 = openai（主）/anthropic（备）/relay（备），全部 env 值。
- `/api/settings` 的 `gateway` 字段改报 `_agent_runtime.model_configured()`（原为网关 /healthz 探活）。

### D3 死代码清除边界

仅删除「只被 openclaw 路径引用」的符号；`_mask`/`_key_configured`/`_mask_key` 等有其他使用者的工具函数保留。清理随之失效的 import（msvcrt/fcntl/urllib.error）与常量（OPENCLAW_PROFILE/CHAT_TRANSPORT/THINKING_LEVEL/SHARED_RAW_STREAM/OPENCLAW_SESSIONS_DIR/RESERVED_PROVIDER_KEYS）。

### D4 模块与依赖删除

- 删除 `easel/{gateway_endpoint,gateway_questions,openclaw_cmd,openclaw_workspace,local_agents,cli,__main__}.py` 与 `easel/commands/`（OpenClaw 控制 CLI，Web 运行不依赖）；移除 `pyproject.toml` 的 `easel` 控制台入口。
- 移除 `websocket-client`/`cryptography`（仅问答题 gateway WS 桥接使用）。
- 删除 `apps/scripts/gateway.{sh,ps1}`（OpenClaw 网关启动脚本）。

### D5 技能目录归位

Easel 复制期把 `skill-wechat-publisher` 单技能内容平铺进了组目录 `skills/openclaw/`，导致 `WECHAT_SKILL_DIR`（指向不存在的子目录）、`find_skill`/`get_skills`（扫描子目录找 SKILL.md）自复制起即断。归位为 `skills/builtin/skill-wechat-publisher/` 后，app.py 既有路径引用与技能发现逻辑自然生效；`validate_skills.py` 指向 `skills/builtin` 并移除本仓从未随迁技能（bilibili-upload、xhs-analyzer）的契约条目。

### D6 依赖声明修复（验收时暴露）

- `deepagents`/`langchain-core` 显式声明（此前靠旧 venv 手工安装，`uv sync` 按 lock 裁剪即断）。
- `requires-python` 收紧 `>=3.11`（deepagents 硬要求）。
- `biliup==1.2.9`：1.2.11 仅发布 sdist（需 Rust/maturin），1.2.9 为最后带 `cp39-abi3 win_amd64` wheel 的版本（兼容 3.9+）。

### D7 前端对齐

`SettingsPanel.tsx`：移除 local-agents 区块（状态/探测 effect/接入 handler/渲染）、custom 供应商「添加供应商」入口与 chat 板块「设为主」/删行（openclaw.json 时代语义）；`api.ts` 移除 `LocalAgent*` 类型与函数。媒体通道（image/video/music/speech）的 provider 配置与 openclaw 无关，保持不动。

## 数据流（变更后）

```
前端 ──► app.py 端点（/api/chat[/stream]、/api/skill、画像增强）
          └► easel.agent_runtime（ask / ask_sync / run_turn）
               └► deepagents（create_deep_agent，LangGraph checkpoint）
                    ├─ 模型：OPENAI_MODEL/OPENAI_BASE_URL/OPENAI_API_KEY（.env，面板可写）
                    ├─ HITL：ask_human 中断 → question 帧 → /api/chat/question/answer resume
                    └─ 持久化：sessions/<key>.json + checkpoint
```

## 权衡与已知取舍

- `/api/settings/local-agents`（本机 CLI 免 key 接入）随 OpenClaw 运行时一并移除：其语义是「把本机 CLI 写成 openclaw.json 供应商」，在 deepagents 架构下无对应物。
- 问答题 gateway WS 桥接删除：deepagents 的 interrupt/resume 已覆盖同一交互，且不依赖外部网关进程。
- 技能内容本身（SKILL.md 的 metadata.openclaw 清单格式）不动：属上游 skill 文件格式约定，非运行时依赖。
