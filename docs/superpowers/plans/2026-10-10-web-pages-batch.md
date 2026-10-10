---
change: web-pages-batch
design-doc: openspec/changes/web-pages-batch/design.md
base-ref: 1238359
archived-with: 2026-10-10-web-pages-batch
---

<!-- comet-task-authority: openspec/changes/web-pages-batch/tasks.md -->

# 实施计划：web-pages-batch（Easel 页面对齐第二批）

四页+端点：Accounts/Breakdown/Skill(运维)/Settings。决策见 design.md D1-D6。

## 执行序（每项绑定 comet-task-ref）

<!-- comet-task-ref:4a306e12-d7cd-4134-95c9-30f3bfffec55 -->
- T1 core/settings.py 运行时设置 + notify 优先级

<!-- comet-task-ref:3bfedc0c-56c2-457a-bf40-77626101efc8 -->
- T2 accounts_detail 聚合 + toggle 端点

<!-- comet-task-ref:0b464dbd-6a4f-4b9a-b03c-43941886c761 -->
- T3 复盘端点（复用 postmortem 模块）

<!-- comet-task-ref:6e8cc7a4-a0b5-476a-b7a3-7e6e10a57bbf -->
- T4 运维触发标记 + 网关消费

<!-- comet-task-ref:46c85b03-c7ca-45e0-88e3-3512f1c39e51 -->
- T5 tool_catalog + GET /api/tools

<!-- comet-task-ref:8c659f29-663c-406d-b4fa-9b09346a483b -->
- T6 AccountsPage

<!-- comet-task-ref:c5071631-fd58-4ddd-89c6-b086ab114d10 -->
- T7 BreakdownPage（marked+dompurify）

<!-- comet-task-ref:c06040e7-9b12-4cc6-9478-4e83ddad7880 -->
- T8 SkillPage

<!-- comet-task-ref:076e178c-37d4-42ad-8ee5-bdfbdd9e13d0 -->
- T9 SettingsPage

<!-- comet-task-ref:e5c21f02-9253-45ab-bd8f-1f8609ef3bd0 -->
- T10 make check + pnpm build

<!-- comet-task-ref:8d67c767-6208-406c-a152-ac4529e329cb -->
- T11 端点冒烟 + spec 场景核对
