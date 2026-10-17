---
change: autonomous-feedback
design-doc: docs/openspec/changes/autonomous-feedback/design.md
base-ref: a052903
---

# Plan：发布数据回流校准下一轮选题

<!-- comet-task-authority: docs/openspec/changes/autonomous-feedback/tasks.md -->

## G1 汇总与校准 <!-- comet-task-ref:103b7118-0aa9-430a-9ee0-4ee2630f1090 --><!-- comet-task-ref:b003fba7-53aa-40b6-b8bf-cbbd86ada65e -->

collect_published（容错汇总）+ build_calibration（只陈述事实，不虚构）+ 归档。

## G2 注入发现层 <!-- comet-task-ref:4cc3ef81-799f-43a5-adf9-cd3c5acb2cba --><!-- comet-task-ref:cf220eb1-c7f1-45d3-8679-52503649fc03 -->

flows/runner 仅 discover 注入（可关闭）；GET /api/feedback。

## G3 验证 <!-- comet-task-ref:9ef31df4-dc51-40f3-afdf-9fb281e4bdb8 --><!-- comet-task-ref:6532348a-848e-4d38-a2d1-3dd4453ebe13 -->

9 单测 RED→GREEN；端到端探针 PASS；make check 255 passed；E2E 63/63。
