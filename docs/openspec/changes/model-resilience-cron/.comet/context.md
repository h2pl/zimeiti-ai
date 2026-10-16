# Comet Design Handoff

- Change: model-resilience-cron
- Phase: design
- Mode: compact
- Context hash: daeb6f32c60f030637dacd886a4bea4f835e038566f60c3e7b11df5029c53e55

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/model-resilience-cron/proposal.md

- Source: docs/openspec/changes/model-resilience-cron/proposal.md
- Lines: 1-35
- SHA256: 3e47dc722c5f9e079e53f84dd64ac772a3b155ebbfdc32e81168f476bda06551

```md
---
comet_change: model-resilience-cron
---

# model-resilience-cron：模型韧性与定时自动化

## Why

OpenClaw 源码调研（model-failover.md / automations）显示两块我们没有的能力：

1. **模型 fallback 链**：auth-profile 轮换→模型 fallback 链；**用户显式选择的模型严格不 fallback**。我们单一模型直连，主模型一挂（限流/欠费/网络）对话全断。
2. **定时自动化（automations/cron）**：会话级持久化的定时任务与心跳。用户提过「每天早上自动出稿」的运营 case 定时化需求，目前只能手动跑 `run_brand_case.py`。

另缺**会话成本可见性**（OpenClaw 有 usage 滚动统计；我们无任何 token/成本追踪）。

## What Changes

- `_build_model()` 支持 fallback 链：主模型不可用（连接错误/限流/5xx）自动切下一个；用户在设置里显式指定的模型**不** fallback（OpenClaw 同款语义）
- `automations` 端点 + 工具：CRUD 定时任务（cron 表达式或每日时刻），任务体=运营 case 脚本或预置 prompt；服务重启后任务不丢（PG 持久化）；到点执行经既有 ask/chat 链路
- 会话 usage 统计：每轮对话记录 token 用量（PG），`/api/usage` 可按会话/日期查

## Capabilities

### New Capabilities

- `model-fallback`：主模型故障自动切换备用模型，显式选择不降级
- `scheduled-automation`：定时运营任务持久化与到点执行
- `usage-tracking`：会话 token 用量记录与查询

## Non-Goals

- 阶梯定价/成本金额引擎（只记 token 数，不换算钱——无单价数据源）
- 订阅配额窗口与 provider usage 直拉（OpenClaw 的 usage-tracking 后半程）
- standing intents / Prospective 记忆层（②已声明不做）
- heartbeat 心跳协议（单用户场景用 cron 足够）

```

## docs/openspec/changes/model-resilience-cron/design.md

- Source: docs/openspec/changes/model-resilience-cron/design.md
- Lines: 1-60
- SHA256: 181c280f0d98e6a5b9165e8fec761976a1dda24913627baf1f799fef3391e6f7

```md
---
comet_change: model-resilience-cron
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：模型韧性与定时自动化

## 高层方案

```
_build_model()（改造）
  ├─ 读 .env 主模型 + ZIMEITI_FALLBACK_MODELS（逗号分隔，可空）
  ├─ 用户显式选择（设置面板存的显式模型）→ 不 fallback
  └─ 包装 FallbackChatModel：invoke/astream 失败（连接/限流/5xx）→ 链下一个
       （自写 wrapper，不用 langchain 的 with_fallbacks——它不区分错误类型，
         会把 4xx 参数错误也切走，掩盖真实问题）

automations（新模块 zimeiti_api/automations/）
  ├─ PG 表 automations(id, name, cron/时刻, kind[case|prompt], payload, enabled,
  │                last_run, next_run, created_at)
  ├─ lifespan 起调度循环（asyncio，每分钟 tick，到点触发）
  └─ 触发执行：kind=case → asyncio.to_thread 跑 run_brand_case 主函数；
      kind=prompt → 经 ask_sync 走对话链路；结果写 outputs/_automations/<id>/

usage（pg.py 加表 chat_usage(session_key, turn_id, model, prompt_tokens,
      completion_tokens, created_at)）+ /api/usage 查询端点
```

## 关键决策

### D1：fallback 自写 wrapper 而非 with_fallbacks
langchain 的 `with_fallbacks` 对任何异常都切换。我们只对**基础设施类失败**
（APIConnectionError / RateLimitError / 5xx APIStatusError）切换；4xx（参数/鉴权）
直接抛——鉴权失败切备用模型只会把错误藏起来。

### D2：调度用进程内 asyncio tick 而非外部 cron
单用户本地服务，进程内每分钟 tick 足够；任务持久化在 PG 保证重启不丢；避免引
外部依赖（APScheduler 等）。执行与 API 进程同生命周期——服务停了任务不跑
（本地场景可接受，文档注明）。

### D3：定时任务的执行隔离
case 类任务 to_thread 跑（阻塞型脚本，已有成熟实现）；prompt 类任务走
ask_sync（主循环）。两者都写执行日志到 outputs/_automations/。

### D4：usage 只记 token 不换算钱
无单价数据源（OpenClaw 的阶梯定价引擎依赖其 model catalog；我们的模型是
.env 配置的任意端点）。记 token 数+模型名，金额换算留给未来接单价后做。

## 风险与对策

- **风险**：fallback 掩盖主模型配置错误 → 对策：4xx 不切换 + 切换时活动行提示
- **风险**：调度 tick 与服务重启竞态 → 对策：next_run 持久化 + 执行标记（running
  状态带租约时间），重启后过期租约任务重排
- **风险**：定时 case 跑失败无声 → 对策：执行日志落盘 + 失败写入 automation_runs

## Open Questions

无。

```

## docs/openspec/changes/model-resilience-cron/tasks.md

- Source: docs/openspec/changes/model-resilience-cron/tasks.md
- Lines: 1-27
- SHA256: 58168efc56e05391e8d76ad97e3301306a4e125d4332870f1a0c513609be1e7b

```md
---
comet_change: model-resilience-cron
---

# Tasks：模型韧性与定时自动化

## 1. 模型 fallback

- [ ] 1.1 FallbackChatModel wrapper（只对连接/限流/5xx 切换；4xx 直抛）+ 单测（RED→GREEN） <!-- comet-task:5d6f6011-9365-4f42-b9ae-b09c86958426 -->
- [ ] 1.2 `_build_model()` 接入：主模型 + `ZIMEITI_FALLBACK_MODELS` 链；设置面板显式选择的模型不 fallback <!-- comet-task:629a450b-465e-44d9-9bc4-17a981b573be -->
- [ ] 1.3 切换时活动行提示（用户可见） <!-- comet-task:6db22f98-a348-4b49-8b54-e958caf51dd9 -->

## 2. 定时自动化

- [ ] 2.1 `zimeiti_api/automations/`：PG 表 + CRUD 端点（/api/automations） <!-- comet-task:5598dedb-96db-496d-bfa9-a75db5854b5e -->
- [ ] 2.2 lifespan 调度循环（每分钟 tick，next_run 持久化+租约） <!-- comet-task:90f9bef0-2390-488e-b394-0e7d8b1284b9 -->
- [ ] 2.3 执行链路：kind=case（to_thread 跑 run_brand_case）/ kind=prompt（ask_sync）；日志落 outputs/_automations/ <!-- comet-task:58f6c6c2-8a5f-4e1c-8216-b5c94007656e -->

## 3. usage 统计

- [ ] 3.1 chat_usage 表 + 每轮记录（模型/token）+ /api/usage 查询端点 <!-- comet-task:1a88d55e-01a3-4725-a198-d2fd7121de07 -->
- [ ] 3.2 单测 + 探针（fallback 触发可观测） <!-- comet-task:fd549b82-7e17-4212-a7f9-e4625c47d657 -->

## 4. 验证

- [ ] 4.1 make check 全绿；探针：主模型指向坏端点 → 自动切备用且对话完成 <!-- comet-task:e9a54255-ec00-494e-9d02-430368c7fde2 -->
- [ ] 4.2 配置每日自动化 → tick 触发执行 → 日志可查；重启后任务仍在 <!-- comet-task:4ed7e3e4-bbc8-4762-b083-3bc812b285bc -->

```

## docs/openspec/changes/model-resilience-cron/.openspec.yaml

- Source: docs/openspec/changes/model-resilience-cron/.openspec.yaml
- Lines: 1-2
- SHA256: 9cfa2ab963a8c9b58eecdb9fd5b55544e988fee8de8b887226ffc32d27744459

```md
schema: spec-driven
created: 2026-10-16

```

## docs/openspec/changes/model-resilience-cron/specs/model-fallback/spec.md

- Source: docs/openspec/changes/model-resilience-cron/specs/model-fallback/spec.md
- Lines: 1-39
- SHA256: 2fe1b0edddd264452c6a9bf7cc71a8b090a97574e493c344bd8c1a422a8ece85

```md
# model-fallback 规格草案

## Purpose

主模型故障时对话不中断：自动切换备用模型；用户显式指定的模型严格不降级；定时运营任务可持久化配置并按点执行；会话 token 用量可查。

## ADDED Requirements

### Requirement: 模型 fallback 链

模型配置支持主备链；主模型因连接错误/限流/服务端错误失败时，同一轮对话自动改用链上下一个模型重试； fallback 事件在回复活动行可见。

#### Scenario: 主模型故障自动切换
- **WHEN** 主模型请求失败（超时/限流/5xx）
- **THEN** 自动用备用模型完成本轮，用户看到切换提示，对话不中断

#### Scenario: 显式选择不降级
- **WHEN** 用户在设置中显式指定了模型
- **THEN** 该模型失败时不 fallback，直接报错并说明原因

### Requirement: 定时自动化

运营任务可配置为定时执行（每日时刻或 cron）；任务配置持久化，服务重启后仍在；到点执行经既有对话/脚本链路，执行结果可查。

#### Scenario: 每日定时出稿
- **WHEN** 用户配置「每天 08:00 跑运营 case」
- **THEN** 到点自动执行，产出落在内容库，执行记录可查

#### Scenario: 重启后任务仍在
- **WHEN** 服务重启
- **THEN** 已配置的定时任务不丢失，按原计划继续

### Requirement: 会话用量统计

每轮对话记录 token 用量（按会话/轮次/模型）；可查询会话与日期范围的用量汇总。

#### Scenario: 查询会话用量
- **WHEN** 查询某会话的用量
- **THEN** 返回该会话各轮次的 token 数与所用模型

```
