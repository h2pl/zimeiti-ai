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
