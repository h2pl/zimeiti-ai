---
comet_change: feat-chat-resume-tools
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-12-feat-chat-resume-tools
status: final
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
