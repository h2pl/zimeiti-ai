# chat-workbench Specification

## Purpose
TBD - created by archiving change web-chat-publish. Update Purpose after archive.

## Requirements

### Requirement: 会话创建与清单

创建对话会话返回唯一 thread_id；清单列出全部会话（含最后活跃时间与轮次数）。

#### Scenario: 创建会话
- **When** POST /api/chat/sessions
- **Then** 返回唯一 thread_id，会话出现在清单中

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

### Requirement: 发布中心

发布中心列出内容库草稿与发布队列；可将草稿入队（复用 publish_queue 幂等
语义：同键重复入队被拒绝）；队列状态随处理回填。

#### Scenario: 重复入队被拒绝
- **When** 同一 source_folder+publish_date 已在队列
- **Then** 入队返回已存在错误，队列不产生重复条目

### Requirement: 工具事件帧

chat_stream 在 agent 执行工具步骤时下发 tool 帧（含工具/节点名与状态），
前端渲染为系统状态行。

#### Scenario: 发布调用可见
- **When** agent 执行 publish 工具
- **Then** 对话流中出现「正在调用 publish」状态行
