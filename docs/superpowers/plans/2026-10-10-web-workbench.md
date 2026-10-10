---
change: web-workbench
design-doc: openspec/changes/web-workbench/design.md
base-ref: 89ee64466e2057ae848d1151189ddae389e90827
---

<!-- comet-task-authority: openspec/changes/web-workbench/tasks.md -->

# 实施计划：web-workbench（Web 运营工作台）

对标 Easel web/frontend 的路由化多页工作台。任务 T1-T10 见 tasks.md（authority）。

执行序：
- 后端三组端点（T1 dashboard / T2 profiles / T3 trends+outputs）——每项带测试
- 前端路由化（T4 router+layout → T5 api 客户端+页面拆分 → T6 四新页 → T7 pnpm build）
- 验证（T8 make check / T9 冒烟+build 证据 / T10 spec 场景核对）

回滚：单 commit revert。风险：画像 PUT 是唯一受控写端点（D3 双保险）。
