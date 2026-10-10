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
