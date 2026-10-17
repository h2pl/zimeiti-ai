---
change: autonomous-observability
design-doc: docs/openspec/changes/autonomous-observability/design.md
base-ref: d512769
archived-with: 2026-10-18-autonomous-observability
---

# Plan：自主运营看板

<!-- comet-task-authority: docs/openspec/changes/autonomous-observability/tasks.md -->

## G1 后端执行记录 <!-- comet-task-ref:668af003-d465-490b-816f-01aef2eed0fa -->

store.list_runs（flow_id 过滤+步骤明细）+ GET /api/flows/runs；单测。

## G2 前端看板 <!-- comet-task-ref:55185f22-f446-4c05-9cc7-1f3b99c74d45 --><!-- comet-task-ref:6cc45dc2-26b2-4fa8-92e8-e9c3f7ccc5b2 -->

api.ts 封装 + AutonomousPage（严格克隆 AutomationsPage 范式 D1）+ 导航；构建+截图目检。

## G3 验证与文档 <!-- comet-task-ref:36781286-1074-440f-b278-39fc5f19bfc7 --><!-- comet-task-ref:96c2f510-7fe9-4b14-a4a3-faf276e45191 -->

E2E S13（zimeiti 独有 → NOTE）+ 全量 13 场景；demo 第 6 段 + README 章节；make check 全绿。
