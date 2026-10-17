---
change: autonomous-flow
design-doc: docs/openspec/changes/autonomous-flow/design.md
base-ref: 35de70b
archived-with: 2026-10-18-autonomous-flow
---

# Plan：运营流程编排

<!-- comet-task-authority: docs/openspec/changes/autonomous-flow/tasks.md -->

## G1 包与持久化 <!-- comet-task-ref:5d41d363-aa40-4c4a-a6a1-ee9737e3affd --><!-- comet-task-ref:873f6b21-b809-4395-af20-1c54f8b31d52 -->

zimeiti_autonomous 包（flows 五层枚举与裁剪/store 三表幂等建表/CRUD 单测）。

## G2 编排执行与调度分发 <!-- comet-task-ref:b363ec57-9b8e-438b-b93d-f1211be54b59 --><!-- comet-task-ref:fd8044e8-39dd-4328-af2e-61a20ecc4f7a --><!-- comet-task-ref:20238ef8-9d25-4587-b97a-ca697fb1c402 -->

runner 串行执行（摘要链+逐步归档+失败即停）；set_agent_entry 注入纪律；
automations kind=flow 分发 + /api/flows 端点；既有 case/prompt 不回归。

## G3 验证 <!-- comet-task-ref:1e7568f6-542f-4cb5-91a7-e18a7a2143cd --><!-- comet-task-ref:1cccd857-90bb-4da4-a3fb-e62ec00e96eb -->

8 单测 RED→GREEN；端到端探针 PASS；make check 246 passed；E2E 63/63。
