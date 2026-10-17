---
change: harness-business-split
design-doc: docs/openspec/changes/harness-business-split/design.md
base-ref: a7b175a
archived-with: 2026-10-17-harness-business-split
---

# Plan：harness/business 分层

<!-- comet-task-authority: docs/openspec/changes/harness-business-split/tasks.md -->

## G1 包落位与依赖倒置 <!-- comet-task-ref:e281761b-f2a2-4763-b469-83df3408076a --><!-- comet-task-ref:159be7ae-7493-4ff6-bf6f-eb24bc1f3d9c --><!-- comet-task-ref:7a042994-ee11-4c91-87ae-ce17130c6e53 -->

zimeiti_harness 建包（runtime 五模块+memory+usage）；contract.py 注入点；
agent_runtime._skills_catalog 走 contract；chat/status 路由归位 zimeiti_api 顶层。

## G2 注入与守卫 <!-- comet-task-ref:a3ad1618-d8bb-458c-b0d9-ba5575e41724 --><!-- comet-task-ref:f5b20336-9ead-4da4-b58e-2da55c24114c --><!-- comet-task-ref:28c2fda5-d03d-4fe9-bd2e-e9446256d596 -->

scheduler set_ask_sync 注入（app.py 接线）；分层守卫测试（禁业务域 import、
core 白名单、scheduler 注入纪律）；pyproject/Makefile 范围同步 + 全库 import 更新。

## G3 验证 <!-- comet-task-ref:8c685111-1104-46c6-99d6-6f87b3fc3e65 --><!-- comet-task-ref:a1d4f40a-b2ad-45a1-b9d9-2a461c3068e4 -->

make check 234 passed（含 5 项分层守卫）；make evals（402 余额暂阻，见报告）；
E2E 63/63；探针行为一致。
