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

重试的可用范围由**后端能力**决定并以代码注释如实说明：后端对话历史从 PG checkpoint 重放、chat/stream 不带历史且不支持截断参数（G1 探针实测），因此重试限最后一轮；待后端支持服务端截断后，前端限制同步放开。前端不得保留「非最后一轮就拦下」的**无理由**本地限制，也不得把历史运行时语义当作限制理由。

#### Scenario: 重试范围与理由一致
- **WHEN** 用户查看任意轮次的重试入口
- **THEN** 最后一轮可重试；非最后一轮不可重试，且代码中以现行后端事实说明原因（而非引用已退役运行时的语义）

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
