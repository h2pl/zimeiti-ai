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
