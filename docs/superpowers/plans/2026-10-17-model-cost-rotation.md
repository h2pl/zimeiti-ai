---
change: model-cost-rotation
design-doc: docs/openspec/changes/model-cost-rotation/design.md
base-ref: bef4762
archived-with: 2026-10-17-model-cost-rotation
---

# Plan：成本折算与多 key 轮换

<!-- comet-task-authority: docs/openspec/changes/model-cost-rotation/tasks.md -->

## G1 定价模块 <!-- comet-task-ref:b1bd4bc0-4dac-4503-847f-964c8d9354c7 --><!-- comet-task-ref:a12211ad-e992-446f-bc66-01b411c29b90 -->

runtime/pricing.py：MODEL_PRICING 常量表（注明更新日期）+ cost_usd() 纯函数
（未知/空模型 None；容错 模型名@base_url 与大小写）；单测覆盖。

## G2 usage 接线 <!-- comet-task-ref:7b4d3cc3-9905-451d-ae7a-96488b9e6384 --><!-- comet-task-ref:890182af-3408-4eb1-89a0-4b258602b006 -->

summary() 行级+总计 cost_usd（None 不计、partial 标注）；前端 UsageCard 金额展示。

## G3 key 轮换 <!-- comet-task-ref:d71e66da-71c5-4915-b2fa-32a4b4bdb0eb --><!-- comet-task-ref:57733794-391b-44da-aca2-a3fa203bca4f -->

_build_model：ZIMEITI_API_KEYS 多 key 前置链（复用 FallbackChatModel，零新机制）；
on_switch 区分 [key-rotation]/[model-fallback]；未配置行为不变；显式模型不轮换。

## G4 验证 <!-- comet-task-ref:35ff692f-4f67-4875-91ad-fe9789a3caf2 --><!-- comet-task-ref:1252e199-6d31-402c-9bdf-55f83fc4e743 -->

make check + make evals 双绿；端到端探针（轮换日志 + usage 金额字段）。
