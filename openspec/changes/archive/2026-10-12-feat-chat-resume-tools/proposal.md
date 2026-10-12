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
