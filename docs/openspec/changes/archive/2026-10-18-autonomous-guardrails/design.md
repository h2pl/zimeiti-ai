---
comet_change: autonomous-guardrails
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-18-autonomous-guardrails
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
