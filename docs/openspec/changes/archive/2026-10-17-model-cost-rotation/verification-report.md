---
comet_change: model-cost-rotation
---

# 验证报告：model-cost-rotation（成本折算与多 key 轮换）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 已知模型折算 | ✅ | 端到端探针：usage 返回 `cost_usd=$0.003419`（deepseek-chat 12659/1 token），`partial=false`；单测验证按输入/输出分别计价 |
| 未知模型不编造 | ✅ | 单测：未知/空模型 `cost_usd=None`；usage 有未知行时 `cost_usd_partial=true`、总计只含已知部分；前端显示「部分模型未计价」 |
| 限流先换 key | ✅ | 端到端探针（主模型指坏端点 + 2 key + 备用模型）：日志顺序 `[key-rotation] key#1 失败换 key#2` → `[model-fallback] 切换备用模型` → 正常回复「收到收到」 |
| 未配置多 key 行为不变 | ✅ | 单测：不设 `ZIMEITI_API_KEYS` 时链长与原行为一致；单 key 不重复节点 |

## 自动化验证

- **单测**：`test_cost_rotation.py` 10 项 RED→GREEN（定价/None 语义/@容错/usage 接线/链构造顺序/开关组合）
- **`make check`**：全绿（exit 0）——229 passed
- **`make evals`**：5/5 通过（行为层无回归）
- **前端**：tsc + vite build 通过

## 实现要点

- key 轮换**复用** FallbackChatModel（model-resilience-cron 已验证的逐项切换 +
  基础设施失败判定），「主模型×各 key」只是链上前置节点——零新机制（design D2）
- 4xx（含坏 key 的 401）仍然直抛：与「不掩盖配置错误」一致（design 风险节）
- 备用模型沿用 `keys[0]`（D3）：备用计费 key 需独立时调 `ZIMEITI_API_KEYS` 顺序即可

## 结论

「花了多少钱」可回答（有价目时），key 限流自愈先于模型切换。**建议通过。**
