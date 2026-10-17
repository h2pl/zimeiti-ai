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
