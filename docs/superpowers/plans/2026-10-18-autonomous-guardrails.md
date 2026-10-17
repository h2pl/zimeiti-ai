---
change: autonomous-guardrails
design-doc: docs/openspec/changes/autonomous-guardrails/design.md
base-ref: 0486563
---

# Plan：无人值守护栏

<!-- comet-task-authority: docs/openspec/changes/autonomous-guardrails/tasks.md -->

## G1 护栏实现 <!-- comet-task-ref:f47a61bb-7554-41b7-9ef8-1a531239244f --><!-- comet-task-ref:c6588c95-6505-4388-8b00-7713bcb963b9 --><!-- comet-task-ref:3bb913d8-0140-4135-b339-91756501af0b -->

步骤级重试（配置性错误不重试）+ 连续失败熔断（成功后归零）+ 预算护栏（无单价放行）。

## G2 自主模式 HITL 策略 <!-- comet-task-ref:4dbe9de5-2332-4217-830f-ab5bc4671ee4 --><!-- comet-task-ref:96073699-9e18-4565-9f60-dd56a3f9dc10 -->

需确认动作标 blocked 且继续；runner 接入（配置驱动可关）+ /api/autonomous/status。

## G3 验证 <!-- comet-task-ref:b713d152-5e7b-448b-a4e3-590838037ede --><!-- comet-task-ref:fb033616-11c1-4c68-ae23-6a0e1f4a92b9 -->

10 单测 RED→GREEN；端到端探针 PASS；make check 265 passed；E2E 63/63。
