# chat-workbench 能力增量（feat-chat-resume-tools）

## ADDED Requirements

### Requirement: 工具事件帧

chat_stream 在 agent 执行工具步骤时下发 tool 帧（含工具/节点名与状态），
前端渲染为系统状态行。

#### Scenario: 发布调用可见
- **When** agent 执行 publish 工具
- **Then** 对话流中出现「正在调用 publish」状态行

## MODIFIED Requirements

### Requirement: 流式对话

发送消息后以 SSE 流式返回模型增量 token 与工具事件帧；agent 命中人工闸门时
下发携带载荷的 interrupt 帧并结束本轮流。

#### Scenario: 提问中断以 interrupt 帧下发
- **When** agent 调用 ask_human 触发中断
- **Then** SSE 流以 interrupt 帧结束，pending 队列登记该会话

#### Scenario: 回答后续跑
- **When** 用户经续跑端点回答（resume-stream，决策构造收口后端）
- **Then** agent 从断点流式续跑，续跑的 token 增量在会话内继续渲染；
  续跑中再次命中闸门时下发 interrupt 帧并登记 pending
