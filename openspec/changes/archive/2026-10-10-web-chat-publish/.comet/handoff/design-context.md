# Comet Design Handoff

- Change: web-chat-publish
- Phase: design
- Mode: compact
- Context hash: 7b3936c50d5babb193934e4a9d70af366f5e29e0b7be83274c111aea461239fc

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/web-chat-publish/proposal.md

- Source: openspec/changes/web-chat-publish/proposal.md
- Lines: 1-43
- SHA256: f54e8f4054d0fb510a0dfa6da3e48e3d8b3e33386cac2a3ea0001a9529cb31df

```md
# 提案：对话工作台与发布中心（web-chat-publish）

## Why

Easel 页面清单最后两页：ChatPage（agent 流式对话——PRD「工作台形态」的核心：
用户在对话中驱动 agent 完成选题→创作→审批，提问卡片内联呈现）与 PublishPage
（发布中心：内容库草稿的排期入队与状态跟踪）。二者的后端能力大多已就绪
（deepagents agent + Postgres checkpointer + publish_queue），缺的是会话端点、
SSE 流式协议与 UI。

## What Changes

- 后端：
  - `POST /api/chat/sessions`：创建对话会话（thread_id 注册）
  - `GET /api/chat/sessions`：会话清单
  - `POST /api/chat/sessions/{thread_id}/stream`：发送消息，SSE 流式返回
    （帧类型：token / tool / interrupt / done / error；token 为模型增量输出）
  - 复用既有审批/提问 pending 机制——中断以 interrupt 帧下发，回答经既有
    answer/confirm 端点后再发一条空消息流式续跑
- 前端：
  - ChatPage：会话列表 + 消息流（打字机 token 渲染）+ 输入框 + 内联问题卡片
  - PublishPage：内容库草稿选择 → 入发布队列 → 队列状态列表（对接 publish_queue）
- 依赖：无新增（SSE 用原生 fetch ReadableStream）

## Capabilities

- **New Capabilities**: `chat-workbench`（对话会话与 SSE 流式协议）、
  `publish-center`（发布中心 UI 与入队行为）
- **Modified Capabilities**: 无

## Non-Goals

- 打字机逐字流式的取消/重生成（MVP 用整段增量拼接）
- 多模型切换、会话导出
- 发布中心不做富文本编辑（草稿以内容库产物为准）

## 关键决策

- D1 会话即 LangGraph thread_id（checkpointer 持久化，断点续跑天然支持）
- D2 SSE 帧协议：`event: <type>\ndata: <json>\n\n`；token 增量来自
  `astream(stream_mode="messages")`；interrupt 帧携带问题/审批载荷
- D3 对话中断的恢复复用既有 pending + decisions 端点（不另起炉灶）
- D4 发布中心入队复用 publish_queue（幂等 mark 语义不变）

```

## openspec/changes/web-chat-publish/design.md

- Source: openspec/changes/web-chat-publish/design.md
- Lines: 1-43
- SHA256: dea5890db94a7de0ebb60dc2a3b16803f8cb9875b14eb7d0cbdef5e247ed6454

```md
---
comet_change: web-chat-publish
role: technical-design
canonical_spec: openspec
---

# 设计：web-chat-publish

## Context

Easel 页面清单最后两页。后端已有：deepagents agent（interrupt_on 三闸门）、
AsyncPostgresSaver checkpointer、publish_queue（幂等 mark）、pending 审批机制。
参考: Easel api.ts 的 streamChat（POST + ReadableStream 手解 SSE 帧，
事件类型 token/thinking/error/done + AbortController）。

## Goals / Non-Goals

- Goals：流式对话（token 增量 + 中断卡片内联）、发布中心（入队+队列状态）
- Non-Goals：打字机取消/重生成、多模型切换、富文本编辑

## 决策记录

- **D1 会话=thread_id**：POST /api/chat/sessions 生成 `chat-<uuid>` 并注册到
  data/state/chat-sessions.json；会话即 checkpointer 线程，断点续跑天然支持。
- **D2 SSE 协议**：`POST /api/chat/sessions/{tid}/stream` body {message}，
  StreamingResponse 逐帧 `event: <type>\ndata: <json>\n\n`。类型：token
  （astream stream_mode="messages" 的 AI 增量）/ tool（工具开始结束）/
  interrupt（闸门载荷）/ done / error。流结束时不删 pending（闸门恢复走
  既有 confirm/answer 端点，恢复后的续跑是新的 stream 请求）。
- **D3 会话消息历史**：MVP 不做独立历史存储——页面消息流 = 前端本地状态；
  agent 侧历史由 checkpointer 承载。刷新后消息流从 checkpointer 重建
  （GET /api/chat/sessions/{tid}/messages 读 state.messages）。
- **D4 发布中心入队**：POST /api/publish-queue/enqueue {platform,title,
  source_folder,publish_date} → publish_queue.schedule（幂等）；GET
  /api/publish-queue 列表。入队不直接发布——仍走网关/审批消费。
- **D5 中断卡片复用**：interrupt 帧载荷即 hosted.extract_interrupt_payload
  的产物（question/approval 两类），前端按 kind 渲染卡片，动作走既有端点。

## 风险

- astream 在 TestClient 下需要 async 测试（pytest-asyncio 已配置）
- sync saver/async saver 混用约束：chat 流式统一 AsyncPostgresSaver
  （get_checkpointer），与触发器一致；审批恢复端点维持 sync saver（表结构相同）

```

## openspec/changes/web-chat-publish/tasks.md

- Source: openspec/changes/web-chat-publish/tasks.md
- Lines: 1-20
- SHA256: 8f0eda593edb47a026d852fa43d1c564e8ec8bea5e8b36c1ca71a36546790686

```md
# 任务：web-chat-publish

## 1. 后端

- [ ] T1 `runtime/chat.py`：会话注册（create/list/registry 持久化）+ 测试
- [ ] T2 流式端点：`POST /api/chat/sessions/{tid}/stream`（astream messages
      增量 + interrupt 帧 + done/error 帧）+ 测试（fake agent）
- [ ] T3 `GET /api/chat/sessions/{tid}/messages`（checkpointer state 重建）+ 测试
- [ ] T4 发布中心端点：enqueue（幂等复用 publish_queue）+ 队列列表 + 测试

## 2. 前端

- [ ] T5 ChatPage：会话列表+消息流+SSE 消费+内联问题卡
- [ ] T6 PublishPage：内容库草稿选择+入队+队列状态
- [ ] T7 导航接线（Chat/发布中心）+ pnpm build

## 3. 验证

- [ ] T8 make check + pnpm build
- [ ] T9 端点冒烟 + spec 场景核对

```

## openspec/changes/web-chat-publish/.openspec.yaml

- Source: openspec/changes/web-chat-publish/.openspec.yaml
- Lines: 1-2
- SHA256: e61703315c59969805e021ec521ca189369aaf8ea902d52c5e39c7fbc603598f

```md
schema: spec-driven
created: 2026-10-10

```

## openspec/changes/web-chat-publish/specs/chat-workbench/spec.md

- Source: openspec/changes/web-chat-publish/specs/chat-workbench/spec.md
- Lines: 1-33
- SHA256: 1809c4da2763943a922af36e2c4b2e9277c2aba4bc8631eca9feeaa3c4716590

```md
# chat-workbench 能力增量

## ADDED Requirements

### Requirement: 会话创建与清单

创建对话会话返回唯一 thread_id；清单列出全部会话（含消息数与最后活跃时间）。

#### Scenario: 创建会话
- **When** POST /api/chat/sessions
- **Then** 返回唯一 thread_id，会话出现在清单中

### Requirement: 流式对话

发送消息后以 SSE 流式返回模型增量 token、工具调用事件；agent 命中人工闸门时
下发 interrupt 帧（含问题载荷或审批提示）并结束本轮流。

#### Scenario: 提问中断以 interrupt 帧下发
- **When** agent 调用 ask_human 触发中断
- **Then** SSE 流以 interrupt 帧结束，pending 队列登记该会话

#### Scenario: 回答后续跑
- **When** 用户经应答端点回答后再次发起空消息流
- **Then** agent 从断点续跑并继续流式输出

### Requirement: 发布中心

发布中心列出内容库草稿与发布队列；可将草稿入队（复用 publish_queue 幂等
语义：同键重复入队被拒绝）；队列状态随处理回填。

#### Scenario: 重复入队被拒绝
- **When** 同一 source_folder+publish_date 已在队列
- **Then** 入队返回已存在错误，队列不产生重复条目

```

## openspec/changes/web-chat-publish/specs/publish-center/spec.md

- Source: openspec/changes/web-chat-publish/specs/publish-center/spec.md
- Lines: 1-16
- SHA256: 1341f4d0de6fa28e3cccd7416f418398214cf429342e670d0792415e7f70c5b7

```md
# publish-center 能力增量

## ADDED Requirements

### Requirement: 草稿排期入队

发布中心可将内容库草稿入发布队列：入队复用 publish_queue（同键重复入队
被拒绝）；入队后由既有审批/网关链路消费。

#### Scenario: 重复入队被拒绝
- **When** 同一 source_folder+publish_date 已在队列
- **Then** 返回已存在错误，队列不产生重复条目

#### Scenario: 空内容库账号
- **When** 账号无草稿产物
- **Then** 返回空列表而非报错

```
