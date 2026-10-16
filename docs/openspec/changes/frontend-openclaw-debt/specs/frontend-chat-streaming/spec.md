# frontend-chat-streaming 规格草案

## Purpose

前端对话链路的行为契约与后端（deepagents + PG + SSE）对齐：流式 token 直渲染、重试按会话重放、HITL 卡片直连 question 事件——移除对已退役 OpenClaw 运行时的语义依赖，使后续对话功能演进不被旧假设绊住。

## ADDED Requirements

### Requirement: 流式渲染契约

对话消息流式渲染直接消费 SSE token 帧，允许带节流（合并高频帧，防逐字符 DOM 写入），不依赖任何「上游攒批」假设。

#### Scenario: 长回复流畅渲染
- **WHEN** agent 生成千字以上回复
- **THEN** 前端以稳定节奏增量渲染，无整段空白后跳变

### Requirement: 重试语义

失败重试不受「仅最后一轮」限制：任意历史会话轮次的重试按会话重放语义发起，与后端 checkpoint 重放行为一致；成功重试后本地消息列表与服务端一致。

#### Scenario: 历史轮次重试
- **WHEN** 用户对历史会话中的失败/不满意轮次发起重试
- **THEN** 请求被后端接受并产生新的续跑（或被后端以明确理由拒绝时，前端如实呈现原因），前端不再做「非最后一轮就拦下」的本地限制

### Requirement: HITL 卡片直连

问答卡片直接消费 SSE `question` 事件载荷并 POST `/api/chat/question/answer` 应答；不经过任何 RPC 桥接层语义。

#### Scenario: 选项应答续流
- **WHEN** agent 发起 ask_human 中断
- **THEN** 前端渲染选项卡片，用户选择后应答并在同一 SSE 流中看到续跑输出

### Requirement: 无过时运行时假设

前端代码中不保留对已退役运行时（OpenClaw）的行为规避逻辑与误导性注释；仍需保留的机制（如双开会话防撞）注释须说明现行理由。

#### Scenario: 代码可读性
- **WHEN** 阅读对话链路前端代码
- **THEN** 注释与逻辑均反映现行后端语义，无「openclaw 攒批/takeover」等历史残留
