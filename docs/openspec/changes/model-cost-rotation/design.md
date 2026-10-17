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
