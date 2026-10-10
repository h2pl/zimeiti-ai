---
change: web-workbench
design-doc: openspec/changes/web-workbench/design.md
base-ref: 89ee64466e2057ae848d1151189ddae389e90827
archived-with: 2026-10-10-web-workbench
---

<!-- comet-task-authority: openspec/changes/web-workbench/tasks.md -->

# 实施计划：web-workbench（Web 运营工作台）

对标 Easel web/frontend 的路由化多页工作台。任务 T1-T10 见 tasks.md（authority）。

执行序（每项绑定 comet-task-ref）：
<!-- comet-task-ref:2c863dd4-8ade-4b32-9cde-fb16c551be4b -->
- T1 dashboard
<!-- comet-task-ref:b071bdf4-d6a6-4508-ad3b-24ffe3ca27d3 -->
- T2 profiles
<!-- comet-task-ref:b5c8c120-e540-4058-b761-d10e7f69a9fc -->
- T3 trends+outputs
<!-- comet-task-ref:53af429a-26e0-4f1c-9d5b-29da24593523 -->
- T4 router+layout
<!-- comet-task-ref:43dfdadf-293c-4115-b5db-af1732079320 -->
- T5 api 客户端+页面拆分
<!-- comet-task-ref:934929e1-2771-4c34-a5e5-772a395255aa -->
- T6 四新页
<!-- comet-task-ref:703e5394-d82c-48ba-abee-1533340ddd86 -->
- T7 pnpm build
<!-- comet-task-ref:ec03c37e-90a6-4274-ab4a-df63a2b77b80 -->
- T8 make check
<!-- comet-task-ref:4930c6a5-f6ad-4112-858e-8d06569e8b88 -->
- T9 冒烟+build 证据
<!-- comet-task-ref:76f47c71-d8d2-4edd-884a-fb0d8273a4cc -->
- T10 spec 场景核对

回滚：单 commit revert。风险：画像 PUT 是唯一受控写端点（D3 双保险）。
