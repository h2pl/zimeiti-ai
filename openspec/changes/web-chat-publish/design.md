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
