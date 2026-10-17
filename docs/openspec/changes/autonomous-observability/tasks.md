---
comet_change: autonomous-observability
---

# Tasks：autonomous-observability

## 1. 后端执行记录

- [x] 1.1 store.list_runs（flow_id 过滤 + 步骤明细）+ GET /api/flows/runs；单测 <!-- comet-task:668af003-d465-490b-816f-01aef2eed0fa -->

## 2. 前端看板

- [x] 2.1 api.ts 类型与封装（flows/runs/status/feedback）+ AutonomousPage.tsx（严格克隆 AutomationsPage 范式 D1） <!-- comet-task:55185f22-f446-4c05-9cc7-1f3b99c74d45 -->
- [x] 2.2 侧栏导航「自主运营」+ 路由挂载；构建 + 截图目检 <!-- comet-task:6cc45dc2-26b2-4fa8-92e8-e9c3f7ccc5b2 -->

## 3. 验证与文档

- [x] 3.1 E2E 新增 S13 场景（zimeiti 独有 → parity NOTE）+ 全量 13 场景通过 <!-- comet-task:36781286-1074-440f-b278-39fc5f19bfc7 -->
- [x] 3.2 demo 第 6 段录制 + README「自主运营」章节；make check 全绿 <!-- comet-task:96c2f510-7fe9-4b14-a4a3-faf276e45191 -->
