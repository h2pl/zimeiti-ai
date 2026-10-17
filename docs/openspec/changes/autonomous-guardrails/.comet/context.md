# Comet Design Handoff

- Change: autonomous-guardrails
- Phase: design
- Mode: compact
- Context hash: bc1e683b85b08858bf99ea08cb6781eed45230ab57119554ec92d5c115bac6c7

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/autonomous-guardrails/proposal.md

- Source: docs/openspec/changes/autonomous-guardrails/proposal.md
- Lines: 1-55
- SHA256: c546e6f87f15496924d8e5b8263ecaf465f5813ddd6655c7af442da236f5769b

```md
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

```

## docs/openspec/changes/autonomous-guardrails/design.md

- Source: docs/openspec/changes/autonomous-guardrails/design.md
- Lines: 1-60
- SHA256: 34fcd151075a4486a47dcac78b51d9f954accba29cc76b06590888ee59a8f2c8

```md
---
comet_change: autonomous-guardrails
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：autonomous-guardrails

## 高层方案

```
zimeiti_autonomous/guardrails.py
  RETRYABLE / is_retryable(exc)      可重试判定（配置性错误不重试）
  retry_call(fn, tries, backoff)     步骤级重试（退避递增）
  CircuitBreaker                     连续失败计数 → 达阈值停用（store 持久化原因）
  BudgetGuard                        当日累计成本（chat_usage.cost_usd）比对上限；
                                     无单价 → 放行（不臆造）
  AutonomyPolicy                     付费/发布/不可逆 → blocked（待确认，不阻塞）
                                     其余 → 自动放行
  status()                           汇总：熔断态 / 当日预算 / blocked 清单

runner.run_flow：guardrails 配置驱动（默认开，可关）
router：GET /api/autonomous/status
```

## 关键决策

### D1：HITL 策略落在流程层，不改 harness
`ask_human` + `interrupt_on` 是 deepagents 的运行时机制，改它会侵入 harness 且影响
交互对话。护栏只在**流程层**做：把「需确认动作」识别为 blocked 项并继续，等价于
「自主模式下默认保守拒绝该动作」——既不阻塞，也不会在无人时偷偷执行付费/发布。

### D2：识别方式用「动作特征」而非侵入拦截
不改 harness 就看不到工具调用细节。故用**结果侧特征**判定：步骤执行返回中包含
待确认语义（如 pending/hitl/需确认关键词）时标记 blocked。这是保守且诚实的做法——
宁可多标 blocked，也不自作主张放行。

### D3：预算护栏「无数据即放行」
`cost_usd` 对未知模型返回 None（既有设计：不可得则 None，不编造）。护栏沿用同一
诚实原则：无法计量时不拦截，只在可计量时守上限。

### D4：熔断持久化在 store，不靠内存
进程重启不能让熔断态丢失（否则「每天失败一次」照旧）。存 `flows.enabled=false` +
失败原因字段，复用既有表结构（新增列用 ALTER 幂等）。

### D5：重试默认 2 次、退避递增
网络抖动/限流是自主运行最常见的瞬时故障；但重试不能掩盖真实错误——故配置性错误
（EntryNotInjected）永不重试，且每次重试都要在步骤记录里可见。

## 风险与对策

- **风险**：重试放大成本 → 重试次数默认保守（2 次），且受预算护栏约束
- **风险**：blocked 判定误报（关键词命中但实际无需确认）→ 保守误报只是多一条待办，
  不会造成错误执行；清单可见可人工核销
- **风险**：熔断阈值过低误停 → 默认 3 次连续失败，且成功后归零

## Open Questions

无。

```

## docs/openspec/changes/autonomous-guardrails/tasks.md

- Source: docs/openspec/changes/autonomous-guardrails/tasks.md
- Lines: 1-21
- SHA256: c624726d01f2ab1173df9fa7e3cc1ef80277780dd68a6bea493ca0af9ab1dcd5

```md
---
comet_change: autonomous-guardrails
---

# Tasks：autonomous-guardrails

## 1. 护栏实现

- [ ] 1.1 步骤级重试（可重试判定：配置性错误不重试）+ 退避；重试次数落步骤记录 <!-- comet-task:f47a61bb-7554-41b7-9ef8-1a531239244f -->
- [ ] 1.2 连续失败熔断（达阈值自动停用 + 原因持久化；成功后归零） <!-- comet-task:c6588c95-6505-4388-8b00-7713bcb963b9 -->
- [ ] 1.3 预算护栏（当日累计 cost_usd 比对上限；无单价放行不拦截） <!-- comet-task:3bb913d8-0140-4135-b339-91756501af0b -->

## 2. 自主模式 HITL 策略

- [ ] 2.1 AutonomyPolicy：付费/发布/不可逆 → blocked（待确认，不阻塞）+ 继续后续步骤 <!-- comet-task:4dbe9de5-2332-4217-830f-ab5bc4671ee4 -->
- [ ] 2.2 runner 接入护栏（配置驱动，默认开可关）+ GET /api/autonomous/status <!-- comet-task:96073699-9e18-4565-9f60-dd56a3f9dc10 -->

## 3. 验证

- [ ] 3.1 单测（重试/不重试配置错/熔断/成功后归零/超预算即停/无单价放行/blocked 不阻塞）+ 探针 <!-- comet-task:b713d152-5e7b-448b-a4e3-590838037ede -->
- [ ] 3.2 make check 全绿 + E2E 63/63 不回归 <!-- comet-task:fb033616-11c1-4c68-ae23-6a0e1f4a92b9 -->

```

## docs/openspec/changes/autonomous-guardrails/.openspec.yaml

- Source: docs/openspec/changes/autonomous-guardrails/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/autonomous-guardrails/specs/autonomous-guardrails/spec.md

- Source: docs/openspec/changes/autonomous-guardrails/specs/autonomous-guardrails/spec.md
- Lines: 1-60
- SHA256: fdc4778d29b08b8e77fd34404d2cbafec26195dff2f358de17dac64a8107658e

```md
# autonomous-guardrails 规格草案

## Purpose

让自主流程可以无人值守运行：失败可重试、连续失败自动熔断、预算有上限、需人工确认
的动作不阻塞流程但有据可查。

## ADDED Requirements

### Requirement: 步骤级重试

系统 SHALL 对步骤失败按配置重试（默认 2 次，退避递增），且 MUST NOT 重试配置性
错误（如 agent 入口未注入）——配置错误重试无意义。

#### Scenario: 可重试异常被重试
- **WHEN** 某步骤抛可重试异常（如连接错误）
- **THEN** 按配置重试至上限；仍失败则该步标记 failed 并记录重试次数

#### Scenario: 配置性错误不重试
- **WHEN** 抛 `EntryNotInjected`
- **THEN** 立即失败，重试次数为 0

### Requirement: 连续失败熔断

系统 SHALL 统计同一流程的连续失败次数，达到阈值 MUST 自动停用该流程并记录原因，
避免「每天定时失败、无人知晓」。

#### Scenario: 连续失败触发熔断
- **WHEN** 同一流程连续失败达阈值（默认 3 次）
- **THEN** 流程自动置为停用，状态可查（含原因与最近失败时间）

#### Scenario: 成功后计数归零
- **WHEN** 流程成功执行一次
- **THEN** 连续失败计数归零（不因历史失败误熔断）

### Requirement: 预算护栏

系统 SHALL 在流程执行前检查当日累计成本（`chat_usage.cost_usd`），超过上限 MUST
停止执行并如实报告；无单价数据时 MUST NOT 拦截（不编造金额）。

#### Scenario: 超预算即停
- **WHEN** 当日累计成本超过配置上限
- **THEN** 流程不执行，返回「预算上限」原因

#### Scenario: 无单价数据不拦截
- **WHEN** 用量表无法折算金额（cost 为 None）
- **THEN** 护栏放行（视为不可计量，不臆造拦截）

### Requirement: 自主模式 HITL 策略

流程执行到**付费 / 发布 / 不可逆**动作时，系统 SHALL 按策略处理：默认标记为
blocked（待人工确认）并**继续后续步骤**，MUST NOT 阻塞等待人工应答。

#### Scenario: 需确认动作不阻塞
- **WHEN** 流程步骤触发需人工确认的动作
- **THEN** 该步标记 blocked 并记录待确认项，流程继续（不停在原地等应答）

#### Scenario: blocked 可见
- **WHEN** 查询 `GET /api/autonomous/status`
- **THEN** 返回 blocked 清单与熔断态、当日预算用量

```
