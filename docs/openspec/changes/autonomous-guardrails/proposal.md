---
comet_change: autonomous-guardrails
---

# autonomous-guardrails：无人值守护栏（重试/熔断/预算/自主模式 HITL）

## Why

自主运行批次 ③/④：前两个变更让链路能编排、能回流，但**还不敢真的无人值守跑**：

| 缺口 | 现状（grep 级证据） |
|---|---|
| 失败即停，不重试 | `runner.run_flow` 失败即 break，网络抖动/限流一次就整条流程废掉 |
| 无连续失败熔断 | 流程每天定时跑，若配置错误会**每天失败一次、无人知晓** |
| 无预算护栏 | 用量有 `cost_usd`（chat_usage），但流程执行不看预算——可能一夜跑掉大量额度 |
| **HITL 会卡死自主流程** | `ask_human` 触发 deepagents 中断（pending TTL 30 分钟）——自主跑时无人应答，步骤会挂在那里 |

xiaobei 的对应做法是常驻 daemon + 人工可随时介入（IM 通道）；本变更不引入 IM，
改为**策略层**：自主流程遇到需确认动作时不阻塞等待，而是落「待人工确认」记录并
按策略处理（默认保守放行=拒绝该动作并继续/停止可配）。

## What Changes

- `zimeiti_autonomous/guardrails.py`：
  - `retry`：步骤级重试（次数与退避可配，默认 2 次；**仅对可重试异常**，
    `EntryNotInjected` 这类配置性错误不重试）
  - `CircuitBreaker`：连续失败熔断（同一流程连续 N 次失败 → 自动停用并落原因，
    避免「每天定时失败、无人知晓」）
  - `BudgetGuard`：预算护栏（日/次上限，读 `chat_usage` 的 cost_usd；超限即停并
    如实报告；无单价数据时不拦截——不编造金额）
  - `AutonomyPolicy`：自主模式 HITL 策略（付费/发布/不可逆动作默认**需人工**，
    流程内标记为 blocked 并继续后续步骤；其余自动放行）
- `runner.run_flow` 接入护栏（配置驱动，默认开；可关闭便于单测确定性）
- 状态可查：`GET /api/autonomous/status`（熔断态、当日预算用量、blocked 清单）

## Non-Goals

- **不改 harness 的 HITL 机制本身**：ask_human/interrupt 是运行时行为，护栏只在
  **流程层**处理（策略与记录），不动 deepagents 装配
- **不做 IM 通道**（用户明确先不做）：待确认项在界面与 API 可见即可
- **不做前端看板**：`autonomous-observability`
- 不改既有 case/prompt 任务行为

## Capabilities

### New Capabilities

- `autonomous-guardrails`：自主流程具备重试、连续失败熔断、预算上限与自主模式
  HITL 策略，可安全无人值守运行

## Impact

`zimeiti_autonomous` 新增 `guardrails.py`；`runner.py` 接入（配置驱动，默认开）；
新增 `GET /api/autonomous/status`。既有流程在默认配置下行为变化仅为「失败会重试」，
其余一致。
