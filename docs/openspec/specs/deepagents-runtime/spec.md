# deepagents-runtime Specification

## Purpose
定义 deepagents 进程内运行时承载对话链路的行为契约：流式对话、HITL 问题卡、优雅降级与 SSE 兼容性。

## Requirements

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

### Requirement: SSE 契约与 Easel 前端兼容

运行时发出的帧必须被 Easel 前端正确消费：token/thinking/activity/error/done/question。

#### Scenario: 帧格式

- **WHEN** 运行时输出事件
- **THEN** done 帧携带 `sessionKey`，question 帧携带含 id/question/options 的 JSON，与前端解析逻辑一致

### Requirement: HITL 问题卡内联且可恢复

agent 通过 `ask_human` 提问时，问题以 question 帧内联出现且 SSE 连接保持打开；用户回答后 agent 在原连接续流输出，回答后的轮次结果经 `/api/chat/last` 可取回。

#### Scenario: 提问与恢复

- **WHEN** agent 触发 ask_human 中断，用户经 `/api/chat/question/answer` 回答
- **THEN** 问题状态从 pending 变为已消费，agent 以 Command(resume) 续跑并在原 SSE 连接输出后续 token，最终发 done 帧并落盘

### Requirement: 无模型配置时优雅降级

未配置模型环境变量时，服务不得崩溃，须返回明确错误帧。

#### Scenario: 缺少 OPENAI_API_KEY

- **WHEN** 未设置 `OPENAI_API_KEY` 时发起对话
- **THEN** 返回 error 帧（提示配置项）与 done 帧，HTTP 200，服务继续可用

### Requirement: 会话历史持久化

对话历史必须落盘（`apps/sessions/`），跨重启保留；轮次结果写入既有 `_save_turn` 机制供 `/api/chat/last` 断线取回。

#### Scenario: 重启保留

- **WHEN** 服务重启后对同一 session 发起新一轮对话
- **THEN** agent 上下文包含此前消息（历史从落盘文件恢复）

### Requirement: 模型与会话管理不依赖 OpenClaw

模型配置仅经 `.env` 环境变量（`OPENAI_MODEL`/`OPENAI_BASE_URL`/`OPENAI_API_KEY` 等槽位）读写；设置面板不产生、不读取 `openclaw.json`；会话删除端点操作 deepagents 会话文件。

#### Scenario: 模型配置保存与生效

- **WHEN** 用户在设置面板保存 openai 槽位模型配置
- **THEN** 配置写入 `.env`，运行时按 `OPENAI_MODEL`（兜底 `ZIMEITI_MODEL`）构建模型；全流程不出现 `openclaw.json` 读写

#### Scenario: 会话删除

- **WHEN** 客户端调用 `DELETE /api/session/{key}`
- **THEN** 删除 deepagents 会话文件（`sessions/<key>.json` 及其轮次文件）并如实返回删除结果，不访问 OpenClaw 的 sessions 目录
