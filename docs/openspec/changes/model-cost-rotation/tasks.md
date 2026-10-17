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
