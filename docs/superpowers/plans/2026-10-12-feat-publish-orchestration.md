---
change: feat-publish-orchestration
design-doc: openspec/changes/feat-publish-orchestration/design.md
base-ref: 786b284
---

<!-- comet-task-authority: openspec/changes/feat-publish-orchestration/tasks.md -->

# 实施计划：feat-publish-orchestration

任务 T1-T5（comet-task-authority 指向 tasks.md，ID 见 --assign-ids）。

## 执行序

- T1 queue cancelled 语义 → T2 预检端点 → T3 排期/取消端点 → T4 前端编排 → T5 验证

回滚：分支 revert。
