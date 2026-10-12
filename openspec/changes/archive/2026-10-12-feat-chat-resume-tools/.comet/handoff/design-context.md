# Comet Design Handoff

- Change: feat-chat-resume-tools
- Phase: design
- Mode: compact
- Context hash: f8dc1c08dff9b9d350662df18b9d6aacfd4c9062cace8e4faf32a9436ae81c42

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/feat-chat-resume-tools/proposal.md

- Source: openspec/changes/feat-chat-resume-tools/proposal.md
- Lines: 1-33
- SHA256: 5f153972e7e63b76420a42b20bf6f8f291353f2df4df0a8b0658fedd932c3e6c

```md
# 提案：Chat 内联续跑 + 工具事件（feat-chat-resume-tools）

## Why

对齐缺口矩阵 ⚠ 第 1 项：ChatPage 当前回答后同步返回 last_message 回显（非流式），
且无工具事件流。Easel ChatPage 的核心体验是 agent 会话内**断点续跑继续流式输出**
与工具事件可见。

## What Changes

- 后端：
  - `POST /api/chat/sessions/{tid}/resume-stream`：body {message, kind}
    （kind=question→respond 决策；kind=approval→approve；reject 同理）。
    以 Command(resume) + astream 双模式续跑，SSE 帧同 chat_stream
    （token/interrupt/done/error），续跑中再次命中闸门→登记 pending+interrupt 帧。
  - chat_stream 增 tool 帧：astream updates 中工具节点执行时下发
    {tool: 名称, status: "running"|"done"}（前端显示「正在调用 X」）。
- 前端 ChatPage：回答/确认后走 resume-stream 继续流式渲染；tool 帧渲染为
  系统状态行；回答按钮在续跑期间禁用。

## Capabilities

- **Modified Capabilities**: `chat-workbench`（MODIFIED：回答后续跑场景改为
  流式续跑；ADDED：工具事件帧需求）

## Non-Goals

- 不做多会话并行流；不做对话历史虚拟化

## 关键决策

- resume 决策构造收口在后端（前端只传 message+kind）——避免前端拼 decisions 协议
- tool 帧来自 astream updates 的节点名（LangGraph 节点即工具步骤），零侵入

```

## openspec/changes/feat-chat-resume-tools/design.md

- Source: openspec/changes/feat-chat-resume-tools/design.md
- Lines: 1-23
- SHA256: 28c42defec6e6dad35284b6ec625113261569f8a795b2c834b8448682dcce39f

```md
---
comet_change: feat-chat-resume-tools
role: technical-design
canonical_spec: openspec
---

# 设计：feat-chat-resume-tools

## Context

chat_stream 已实现 astream 双模式 SSE；缺口是「回答后的续跑」走同步 answer
端点（last_message 回显）且无工具事件。spec MODIFIED 场景改为流式续跑。

## 决策记录

- **D1 resume-stream 端点**：`POST /api/chat/sessions/{tid}/resume-stream`
  body {message, kind}。决策构造收口后端：kind=question→respond(message)；
  approval→approve；reject→reject。复用 chat_stream 的 SSE 生成逻辑——
  抽公共 `_stream_frames(agent, config, inp)` 生成器，stream/resume 两端点共用。
- **D2 tool 帧**：astream updates 模式的每个节点更新（dict 含单键节点名）
  映射为 tool 帧 {tool: 节点名, status}；__interrupt__ 键除外（走 interrupt 帧）。
- **D3 决策后清理**：resume 前置校验 pending 存在且 kind 匹配（404/400）；
  resume 移除 pending 后若续跑再次中断由流内 re-arm 登记（复用既有逻辑）。

```

## openspec/changes/feat-chat-resume-tools/tasks.md

- Source: openspec/changes/feat-chat-resume-tools/tasks.md
- Lines: 1-6
- SHA256: ba432db31dd6715d5d794d3f1a685179e89ca07126058374bc29a8a1fc9c347b

```md
# 任务：feat-chat-resume-tools

- [ ] T1 后端：_stream_frames 公共生成器抽取 + resume-stream 端点（决策构造/校验）+ 测试
- [ ] T2 后端：tool 帧下发（updates 节点映射）+ 测试
- [ ] T3 前端：ChatPage 接 resume-stream + tool 状态行渲染
- [ ] T4 make check + pnpm build + spec 场景核对

```

## openspec/changes/feat-chat-resume-tools/.openspec.yaml

- Source: openspec/changes/feat-chat-resume-tools/.openspec.yaml
- Lines: 1-2
- SHA256: 1dfdca412094f24473d8b842866201ec26f200b29b17064b03f1e4982c35a7b9

```md
schema: spec-driven
created: 2026-10-12

```

## openspec/changes/feat-chat-resume-tools/specs/chat-workbench/spec.md

- Source: openspec/changes/feat-chat-resume-tools/specs/chat-workbench/spec.md
- Lines: 1-30
- SHA256: 43a77d12e492567be257a0e36e5b92df09bea25b42a17862882cb8db38174d08

```md
# chat-workbench 能力增量（feat-chat-resume-tools）

## ADDED Requirements

### Requirement: 工具事件帧

chat_stream 在 agent 执行工具步骤时下发 tool 帧（含工具/节点名与状态），
前端渲染为系统状态行。

#### Scenario: 发布调用可见
- **When** agent 执行 publish 工具
- **Then** 对话流中出现「正在调用 publish」状态行

## MODIFIED Requirements

### Requirement: 断点续跑（流式）

回答/确认经 `POST /api/chat/sessions/{tid}/resume-stream`（body {message, kind}）
触发断点续跑：后端构造 respond/approve/reject 决策并以 astream 续跑，
返回与 chat_stream 相同的 SSE 帧（token/tool/interrupt/done/error）；
续跑中再次命中闸门→登记 pending+interrupt 帧。前端回答后进入续跑流式渲染。

#### Scenario: 回答后流式续跑
- **When** 用户经 ChatPage 回答问题卡
- **Then** ChatPage 发起 resume-stream，续跑的 token 增量在会话内继续渲染
  （不再以 last_message 回显替代）

#### Scenario: 续跑中再次命中闸门
- **When** 续跑过程中 agent 再次调用闸门工具
- **Then** 下发 interrupt 帧、登记 pending，前端出现新的问题/确认卡片

```
