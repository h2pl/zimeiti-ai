# Comet Design Handoff

- Change: model-cost-rotation
- Phase: design
- Mode: compact
- Context hash: 70bffb44f36f9362673ac40bfe618f33440ebf6ba1a2714c0f5166732397e13b

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/model-cost-rotation/proposal.md

- Source: docs/openspec/changes/model-cost-rotation/proposal.md
- Lines: 1-48
- SHA256: ae9418e94a4747b9d1794456caa00634c33b565d669787cebc0514881a20b71d

```md
---
comet_change: model-cost-rotation
---

# model-cost-rotation：成本折算与多 key 轮换

## Why

批次 harness-maturity 的第 ④ 项（前批交付时留账 pending）：

1. **成本只有 token 没金额**：`/api/usage` 与用量卡片只显示 token 并标注
   「未折算费用」——用户回答不了「这轮花了多少钱」。OpenClaw 有阶梯定价 +
   cache 分桶；我们至少应做到「有单价数据的模型折算，没有的如实标注」。
2. **无 key 轮换**：单 key 限流（429）时直接切备用模型——但备用模型可能同 key
   同限流。OpenClaw 是 auth-profile 轮换**先于**模型 fallback；我们的
   FallbackChatModel 链已具备「逐项切换」机制，只差把「同模型不同 key」作为
   链上节点喂进去。

## What Changes

- **定价表**（`runtime/pricing.py`）：`MODEL_PRICING`（模型名 → 每 1M token
  输入/输出单价 USD）+ `cost_usd(model, prompt, completion)`；未知模型返回
  `None`（不编造，与契约「没有单价数据就不编造金额」一致）
- **usage 接线**：`summary()` 每行与总计增加 `cost_usd`（可得的算，不可得的
  `null`）；`/api/usage` 透传
- **key 轮换**：`ZIMEITI_API_KEYS`（逗号分隔多 key）——`_build_model` 把
  「主模型 × 各 key」作为链上最前置的节点（key1 → key2 → … → 备用模型链）；
  切换日志区分「换 key」与「换模型」
- **前端**：用量卡片展示折算金额（部分模型无单价时显示「部分未计价」）

## Non-Goals

- 阶梯定价 / cache 分桶计价（单一只读单价表足够当前场景）
- 后台自动拉取供应商价目（价目表手工维护，注释注明更新日期）
- 设置面板可编辑 key（沿用「环境变量只读展示」决策）
- 按用户/按 day 聚合成本报表（现按会话/模型聚合够用）

## Capabilities

### New Capabilities

- `usage-pricing`：有单价数据的模型在用量统计中折算金额；无单价的如实标注
- `api-key-rotation`：多 key 轮换先于模型 fallback；切换有日志区分

## Impact

后端新增 1 个模块 + usage.py 小改 + `_build_model` 链构造调整；前端 UsageCard
小改；无新端点（`/api/usage` 增字段）。

```

## docs/openspec/changes/model-cost-rotation/design.md

- Source: docs/openspec/changes/model-cost-rotation/design.md
- Lines: 1-57
- SHA256: e634466b0acaf167e3d5b6ede59114fefbb947d371e1a71f0ca4f2e98eea2828

```md
---
comet_change: model-cost-rotation
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：成本折算与多 key 轮换

## 高层方案

```
runtime/pricing.py（新增）
  MODEL_PRICING: dict[模型名, (输入$/1M, 输出$/1M)]   # 手工维护，注明更新日期
  cost_usd(model, prompt_tokens, completion_tokens) -> float | None

usage.py summary()
  每行 + total 增加 cost_usd（逐行累加，None 不计入；total 为 None 当全部未知）

runtime/agent_runtime.py _build_model()
  keys = ZIMEITI_API_KEYS.split(",")          # 多 key
  chain = [主模型×key1, 主模型×key2, ..., 备用模型×key1, ...]   # 全链共用 FallbackChatModel
  on_switch 日志：i < len(keys) → "[key-rotation] 换 key #n"；否则 "[model-fallback] 换模型"

web UsageCard
  total.cost_usd 非 null → 显示 "$x.xx"；部分 null → 金额 + 「部分未计价」
```

## 关键决策

### D1：单价表手工维护、模块内常量
OpenClaw 的阶梯定价/cache 分桶对我们当前场景过度设计。一张只读表 +
`cost_usd()` 纯函数即可；表头注释写明「价目更新日期」，过期是文档问题不是代码问题。

### D2：key 轮换复用 FallbackChatModel，不新建机制
FallbackChatModel 的逐项切换 + 基础设施失败判定 + on_switch 回调已经验证过
（model-resilience-cron）。「主模型×各 key」只是链上更前置的节点——同一个
ChatOpenAI 换 `api_key`。零新概念。

### D3：链上每节点独立 api_key，fallback 模型用第一个 key
`ZIMEITI_FALLBACK_MODELS` 支持 `模型名@base_url` 跨厂商；其 key 取
`keys[0]`（备用模型的计费 key 通常独立，但配置面不扩张——需要时用户可在
`ZIMEITI_API_KEYS` 里把备用 key 放前面）。

### D4：usage 金额按「行级可得则计、不可得则 null」
一行里模型已知才折算。总计=已知行之和；若存在未知行，`cost_usd_partial=true`
让前端显示「部分未计价」——不把 None 当 0。

## 风险与对策

- **风险**：单价表过期导致金额失真 → 表头注明更新日期；错误单价好过没有（量级对即可）
- **风险**：key 轮换放大 4xx（坏 key 也直抛）→ 不变：4xx 本来就直抛不切换，
  坏 key 的 401 会立即暴露——这是期望行为（与「不掩盖配置错误」一致）

## Open Questions

无。

```

## docs/openspec/changes/model-cost-rotation/tasks.md

- Source: docs/openspec/changes/model-cost-rotation/tasks.md
- Lines: 1-25
- SHA256: 042c989ec6800e0b587ace7efc6d723c72c80760c76f82d6e0055ba06ad5e913

```md
---
comet_change: model-cost-rotation
---

# Tasks：成本折算与多 key 轮换

## 1. 定价

- [ ] 1.1 `runtime/pricing.py`：MODEL_PRICING（deepseek 系为主，注明更新日期）+ `cost_usd()` 纯函数（未知模型 None） <!-- comet-task:b1bd4bc0-4dac-4503-847f-964c8d9354c7 -->
- [ ] 1.2 单测：已知模型折算正确、未知/空模型 None、大小写容错 <!-- comet-task:a12211ad-e992-446f-bc66-01b411c29b90 -->

## 2. usage 接线

- [ ] 2.1 `usage.summary()` 行级+总计 `cost_usd`（None 不计、有未知行标 `cost_usd_partial`）；单测覆盖 <!-- comet-task:7b4d3cc3-9905-451d-ae7a-96488b9e6384 -->
- [ ] 2.2 前端 UsageCard：金额展示 + 「部分未计价」标注 <!-- comet-task:890182af-3408-4eb1-89a0-4b258602b006 -->

## 3. key 轮换

- [ ] 3.1 `_build_model`：`ZIMEITI_API_KEYS` 多 key 前置链（key 轮换先于模型 fallback），on_switch 区分换 key/换模型 <!-- comet-task:d71e66da-71c5-4915-b2fa-32a4b4bdb0eb -->
- [ ] 3.2 单测：链构造顺序、未配置时行为不变、显式模型不受影响 <!-- comet-task:57733794-391b-44da-aca2-a3fa203bca4f -->

## 4. 验证

- [ ] 4.1 make check + make evals 双绿；确定性断言（轮换判定/折算函数入册） <!-- comet-task:35ff692f-4f67-4875-91ad-fe9789a3caf2 -->
- [ ] 4.2 端到端探针：key 轮换链切换日志；usage 金额字段 <!-- comet-task:1252e199-6d31-402c-9bdf-55f83fc4e743 -->

```

## docs/openspec/changes/model-cost-rotation/.openspec.yaml

- Source: docs/openspec/changes/model-cost-rotation/.openspec.yaml
- Lines: 1-2
- SHA256: 4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9

```md
schema: spec-driven
created: 2026-10-17

```

## docs/openspec/changes/model-cost-rotation/specs/usage-pricing/spec.md

- Source: docs/openspec/changes/model-cost-rotation/specs/usage-pricing/spec.md
- Lines: 1-31
- SHA256: 69e9e81cb35442bc5a3cfbbfc88c431b4fc36e472677e72e99b04279d45eee0d

```md
# model-cost-rotation 规格草案

## Purpose

让「花了多少钱」可回答（有单价数据时），让单 key 限流不再直接烧备用模型（key 轮换先于模型切换）。

## ADDED Requirements

### Requirement: 用量金额折算

用量统计对**有单价数据**的模型按 token 折算 USD 金额；**无单价数据**的模型金额为 null 并如实标注，不编造。

#### Scenario: 已知模型折算
- **WHEN** 用量统计包含单价表内模型（如 deepseek-chat）的记录
- **THEN** 该行与总计包含 `cost_usd` 字段，按「输入/输出分别计价」计算

#### Scenario: 未知模型不编造
- **WHEN** 用量记录的模型不在单价表（或模型名为空）
- **THEN** 该行 `cost_usd` 为 null；总计为「已知部分之和」，界面标注「部分未计价」

### Requirement: 多 key 轮换先于模型 fallback

配置 `ZIMEITI_API_KEYS`（逗号分隔）时，模型链前置「主模型 × 各 key」节点；单 key 限流/连接失败先换 key，key 用尽才切备用模型；切换日志区分换 key 与换模型。

#### Scenario: 限流先换 key
- **WHEN** 主模型在 key1 上遇 429/连接错误且配置了多 key
- **THEN** 先以 key2 重试同一模型；全部 key 失败后才进入备用模型链

#### Scenario: 未配置多 key 行为不变
- **WHEN** 未设置 `ZIMEITI_API_KEYS`
- **THEN** 行为与之前完全一致（单 key → 备用模型链）

```
