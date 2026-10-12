# OpenClaw 依赖清单（phase1-easel-api-copy）

复制自 Easel 的后端中，依赖 OpenClaw 的模块与调用点。后续变更将以 deepagents 运行时替换这些模块，替换前前端契约端点保持不变。

## 核心依赖模块

| 模块 | 作用 | 被引用处 | 替换策略 |
|---|---|---|---|
| `easel/openclaw_cmd.py` | 构造 OpenClaw CLI 命令（spawn 网关进程） | app.py 多处（chat/stream 直连） | deepagents 运行时进程内执行 |
| `easel/openclaw_workspace.py` | OpenClaw workspace/会话目录管理 | openclaw_cmd | deepagents 会话存储（线程内/内存+磁盘） |
| `easel/gateway_endpoint.py` | 解析网关 completions/healthz 地址 | app.py `/api/chat/*` | 无需网关——进程内调用 |
| `easel/gateway_questions.py` | `ask_user` 问题桥（gateway `question.*` RPC + Ed25519 设备签名） | app.py `/api/chat/question/*` | deepagents `ask_human` HITL 原生中断 |
| `easel/local_agents.py` | 本地 agent 注册/启停 | app.py `/api/settings/local-agents` | deepagents agent 定义管理 |
| `easel/commands/*.py` | CLI 子命令（gateway/ping/skill/doctor） | cli.py；app.py 经 openclaw_cmd 间接使用 | 由 deepagents 运行时取代 |

## app.py 中的关键调用点

- `/api/chat/stream`、`/api/chat/jobs/{turn}/stream`：spawn OpenClaw → 监听共享 jsonl 原始流（token/tool/done 帧）
- `/api/chat/question/answer`、`/api/chat/question/status`：gateway_questions 桥
- `/api/status`：网关健康探测（`gateway` 字段）
- `/api/skills`、`/api/skill/{name}`：OpenClaw SKILL 目录扫描（SKILLS_DIR=PROJECT_ROOT/skills）
- `/api/settings/models*`、`/api/settings/local-agents`：模型/agent 配置（读写 easel 配置 + OpenClaw 模型注册）

## 当前运行状态

- 服务可启动、`/api/status` 返回 200（`{"gateway":true,"skills":[],"personas":[]}`）
- OpenClaw 可执行文件缺失：对话流式、问答题、技能执行等依赖网关的端点不可用（返回错误/空态）——这正是解耦变更要补齐的部分
- 契约名（`.easel.json`、`EASEL_PROXY`、`easel_*` 存储键）暂保留，解耦变更时统一决策
