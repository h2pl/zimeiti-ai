# deepagents-runtime 变更规格（phase1-remove-openclaw）

## MODIFIED Requirements

### Requirement: 对话链路由 deepagents 运行时承载

deepagents 进程内运行时是唯一 agent 执行路径，不设 OpenClaw 兜底开关：流式 `/api/chat/stream` 与非流式入口（`/api/chat`、`/api/skill`、画像 AI 增强）一律由 deepagents 运行时承载，全程不出现 OpenClaw 进程或 CLI 调用。

#### Scenario: 对话请求走运行时

- **WHEN** 前端发起 `/api/chat/stream` 对话
- **THEN** 事件由 deepagents agent 产生（进程内执行），SSE 帧依次为 activity → token… → done，全程不出现 OpenClaw 进程调用

#### Scenario: 非流式入口走运行时

- **WHEN** 客户端调用 `/api/chat` 或 `/api/skill`
- **THEN** 回答由 deepagents agent 产生（与流式同一运行时、同一会话历史），无 `openclaw agent` CLI 调用

#### Scenario: 兜底开关移除

- **WHEN** 环境设置 `ZIMEITI_RUNTIME=openclaw`
- **THEN** 行为与默认完全相同（仍走 deepagents），不存在可切回的 OpenClaw 网关/CLI 路径

## ADDED Requirements

### Requirement: 模型与会话管理不依赖 OpenClaw

模型配置仅经 `.env` 环境变量（`OPENAI_MODEL`/`OPENAI_BASE_URL`/`OPENAI_API_KEY` 等槽位）读写；设置面板不产生、不读取 `openclaw.json`；会话删除端点操作 deepagents 会话文件。

#### Scenario: 模型配置保存与生效

- **WHEN** 用户在设置面板保存 openai 槽位模型配置
- **THEN** 配置写入 `.env`，运行时按 `OPENAI_MODEL`（兜底 `ZIMEITI_MODEL`）构建模型；全流程不出现 `openclaw.json` 读写

#### Scenario: 会话删除

- **WHEN** 客户端调用 `DELETE /api/session/{key}`
- **THEN** 删除 deepagents 会话文件（`sessions/<key>.json` 及其轮次文件）并如实返回删除结果，不访问 OpenClaw 的 sessions 目录
