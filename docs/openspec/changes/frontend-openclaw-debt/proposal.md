---
comet_change: frontend-openclaw-debt
---

# frontend-openclaw-debt：前端 OpenClaw 语义残留清理

## Why

OpenClaw→deepagents 迁移后，前端仍背着旧运行时的语义假设，代码里留有专门的规避逻辑与注释（实证：App.tsx「避免两个窗口撞同一会话 → openclaw 并发 takeover 崩溃」、打字机队列假设 OpenClaw 攒批、重试只允许最后一轮的 append-only 约束、QuestionCards 的 ask_user RPC 桥）。deepagents/PG 语义下这些假设已不成立：流式 token 粒度可直渲染、会话状态在 PG 可重放、HITL 走 interrupt 事件。残留导致：改对话行为时被旧假设绊住（重试被无理限制）、读代码的人被过时注释误导。

## What Changes

- **打字机队列**：移除「按 OpenClaw 攒批节奏消费」的假设，适配 deepagents 逐 token 帧直渲染（保留节流防抖，不做逐字符 DOM 写入）
- **重试语义**：移除「重试只允许最后一轮」的 append-only 限制——PG checkpoint 语义下按 session/thread 重放合法；重试逻辑对齐后端既有实现
- **QuestionCards**：从「ask_user RPC 桥」语义简化为「消费 SSE question 事件 → POST /api/chat/question/answer」直连（后端契约已稳定）
- **BroadcastChannel 会话防撞**：保留（双开浏览器仍是真实需求），但更新过时注释说明其现行理由
- 过时 OpenClaw 注释/命名全部更新

## Capabilities

### New Capabilities

- `frontend-chat-streaming`：前端对话流式渲染契约——token 直渲染（带节流）、重试按会话重放、HITL 卡片消费 question 事件

## Non-Goals

- 后端任何改动（SSE 协议、chat API 不动）
- 视觉/交互重设计
- SSE 断线重连与 `?after` 游标机制（现状工作良好，不动）
