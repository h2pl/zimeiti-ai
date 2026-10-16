# Comet Design Handoff

- Change: frontend-openclaw-debt
- Phase: design
- Mode: compact
- Context hash: 75a9de5487e3bd436d303fabf7bc365d741ad4af06ea8e900c6f6681555a0ad5

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/frontend-openclaw-debt/proposal.md

- Source: docs/openspec/changes/frontend-openclaw-debt/proposal.md
- Lines: 1-29
- SHA256: fafd5f533f1c8b859d4cc516e6dbc1f00fd48a25bd0ab042fb98af4fec87c3df

```md
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

```

## docs/openspec/changes/frontend-openclaw-debt/design.md

- Source: docs/openspec/changes/frontend-openclaw-debt/design.md
- Lines: 1-48
- SHA256: dc4091c1b5a554d6367c9e51b2fb6aef1ee777468d74aa1e38dbc515867c267f

```md
---
comet_change: frontend-openclaw-debt
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：前端 OpenClaw 语义残留清理

## 高层方案

纯前端重构，后端 SSE/API 契约不动：

```
现状（OpenClaw 残留）                      目标（deepagents 语义）
─────────────────────────────            ─────────────────────────────
打字机队列假设上游攒批，                  token 帧直渲染 + requestAnimationFrame
  队列慢消费造成渲染滞后        →           节流（合并同帧多 token）
重试只允许最后一轮                        移除本地限制：重试=POST 新一轮指令，
  （append-only 本地拦截）      →           会话重放语义由后端 checkpoint 决定
QuestionCards 经 ask_user RPC 桥  →      直连 SSE question 事件载荷 +
                                          POST /api/chat/question/answer
BroadcastChannel 会话防撞        →        保留，注释更新为现行理由（双开防撞），
  （注释还是 openclaw takeover）             不再提 takeover/flock
```

## 关键决策

### D1：不动 SSE 重连与游标
`?after=` 游标续传与自动重连机制现状工作良好且与运行时无关，明确排除在本 change 外（proposal Non-Goals）。

### D2：打字机保留节流而非删除
deepagents token 帧高频到达，逐字符写 DOM 会卡；保留合并渲染（每 ~50ms 批量 flush）——与「移除攒批假设」不矛盾：移除的是**语义依赖**（假设上游一次给一大段），保留的是**渲染性能手段**。

### D3：重试语义先验证后端行为
后端重试/续跑的实际行为（哪个端点、什么参数）在实现前用一次探针确认（起测试服务实测），避免把后端不支持的语义写进前端。若后端确实只支持特定重放形态，前端如实对齐并在 spec 场景中体现——以实测为准，不猜。

### D4：实施顺序
QuestionCards（最小、独立）→ 打字机 → 重试语义 → 注释清理。每步跑一次 S5 浏览器 E2E 兜底。

## 风险与对策

- **风险**：移除重试限制撞上后端真实限制 → 对策：D3 先实测；spec 场景写明「或被后端以明确理由拒绝时如实呈现」
- **风险**：打字机改坏现有流畅度 → 对策：每步 S5 回归；节流参数保守取现值

## Open Questions

无（D3 的实测属于实现期第一步，不阻塞设计）。

```

## docs/openspec/changes/frontend-openclaw-debt/tasks.md

- Source: docs/openspec/changes/frontend-openclaw-debt/tasks.md
- Lines: 1-30
- SHA256: f32a0f834416d19e75f48de10c9c57aa29fb0be8193d71ffb31e5cb4339e9ebf

```md
---
comet_change: frontend-openclaw-debt
---

# Tasks：前端 OpenClaw 语义残留清理

## 1. 探针

- [ ] 1.1 后端重试/续跑行为实测：起测试服务，对历史轮次发起重试请求，记录真实端点/参数/响应（结果回填 design D3 结论） <!-- comet-task:7e436461-d24f-45be-839e-84489b3705ca -->

## 2. QuestionCards 直连

- [ ] 2.1 QuestionCards 组件改为直消费 SSE question 事件载荷 → POST /api/chat/question/answer；移除 ask_user RPC 桥语义与对应代码 <!-- comet-task:af9b1cfb-6ebd-4021-9a6f-2728549ddf80 -->
- [ ] 2.2 S5 浏览器 E2E 回归 <!-- comet-task:5e04b3da-4e4c-4d0e-b720-9ce245d2a3e4 -->

## 3. 打字机渲染

- [ ] 3.1 移除「上游攒批」假设：token 帧直渲染 + rAF/定时合并节流（每 ~50ms flush）；删除对应队列消费逻辑与过时注释 <!-- comet-task:fdc28792-328c-4a1c-bacf-541fff379679 -->
- [ ] 3.2 S5 回归（长回复渲染流畅度人工核对） <!-- comet-task:411e2eba-7494-4cdf-8249-cf94f85b5a0e -->

## 4. 重试语义

- [ ] 4.1 按 1.1 实测结论对齐重试逻辑：移除「仅最后一轮」本地拦截，保留后端明确拒绝时的如实呈现 <!-- comet-task:e4d30db9-ff95-419a-ae12-226d255ef3d4 -->
- [ ] 4.2 S5 回归 <!-- comet-task:ab754b15-4e94-4c2e-85c5-b142baaa1c3d -->

## 5. 收尾

- [ ] 5.1 全局清理 OpenClaw 残留注释/命名（保留机制更新现行理由注释，如 BroadcastChannel 双开防撞） <!-- comet-task:d21f92ec-dc31-4b8c-bccb-a33e93c1ca11 -->
- [ ] 5.2 `make check` 全绿 + tsc 通过 <!-- comet-task:dd919cff-12c3-49bd-ba11-31df3a786fb2 -->
- [ ] 5.3 spec 四条 Requirement 的 Scenario 逐条对照 <!-- comet-task:1ee74603-8390-40ef-b0bf-0b303bed4462 -->

```

## docs/openspec/changes/frontend-openclaw-debt/.openspec.yaml

- Source: docs/openspec/changes/frontend-openclaw-debt/.openspec.yaml
- Lines: 1-2
- SHA256: ad96f2b16d5a44b9af28550e9c22a6c50784a9c97436d73df9b6477230378519

```md
schema: spec-driven
created: 2026-10-16

```

## docs/openspec/changes/frontend-openclaw-debt/specs/frontend-chat-streaming/spec.md

- Source: docs/openspec/changes/frontend-openclaw-debt/specs/frontend-chat-streaming/spec.md
- Lines: 1-39
- SHA256: ca0cd42f15d03ee3cba6dc9a84ec57f54e7119fd7fad3b9ced9070e93302ca7f

```md
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

```
