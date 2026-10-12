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
