---
change: arch-restructure
design-doc: openspec/changes/arch-restructure/design.md
base-ref: 12a98b23a5720a31abb2de8dd58a23e5b85521a4
---

<!-- comet-task-authority: openspec/changes/arch-restructure/tasks.md -->

# 实施计划：arch-restructure（架构重组）

纯移动重构：35 平铺模块 → 6 领域子包。执行序与验收见 tasks.md（T1-T12）。
映射表（唯一权威）：

| 旧 | 新 |
|---|---|
| audit/credentials/credentials_alias/seal/notify/models | core/{audit,credentials,alias,seal,notify,models} |
| compliance/risk/platform_state/preflight/publisher | governance/{...} |
| themes/xhs_readback（散） | platforms/{themes,xhs_readback} |
| topics/creation/dna/templates/profiles | content/{...} |
| ops_metrics/ops_daily/ops_calibration/ops_report_page/postmortem/kanban | operations/{metrics,daily,calibration,report_page,postmortem,kanban} |
| publish_queue | governance/queue |
| graph/tools/hosted/hosted_daily/gateway/checkpoints/health | runtime/{...} |

步骤（每项绑定 comet-task-ref）：
<!-- comet-task-ref:d99041b1-6ff9-4595-bcd0-52d3d378619c -->
- T1 停机 ✅
<!-- comet-task-ref:8daa8fe8-3f6b-41f0-b09e-1ced71bcb140 -->
- T2 git mv 骨架
<!-- comet-task-ref:cf823d95-b612-4be4-b19c-e082ff5ffaa0 -->
- T3 导入重写（脚本化映射，长名优先）
<!-- comet-task-ref:5bc82ca5-e11f-401f-a66e-8c0d6bb5c2f6 -->
- T4 全链 import 检查
<!-- comet-task-ref:e2564449-d736-4b3e-bfc4-07651264618d -->
- T5 入口矩阵（Makefile/bat/scripts）
<!-- comet-task-ref:03f90c4d-1839-43af-a05a-d06e2a67ee0c -->
- T6 测试目录归位
<!-- comet-task-ref:9b7de973-c7fc-4629-b82d-5bf2ed564f88 -->
- T7 batch 测试拆分归位
<!-- comet-task-ref:d8e7cd19-6de3-424a-9e62-1aac66b3bed5 -->
- T8 conftest 与测试导入更新
<!-- comet-task-ref:70797527-1e2f-4c71-aaa4-f77125c9adbc -->
- T9 make check 全绿
<!-- comet-task-ref:ae2e6ed4-818d-4657-962f-fc639f0efd03 -->
- T10 入口冒烟（8 个 python -m + app 导入）
<!-- comet-task-ref:37e3703c-0b7f-4f11-a559-18d47dec1b02 -->
- T11 grep 零残留
<!-- comet-task-ref:e31eafe3-7514-45f2-b278-8bb9adae1e57 -->
- T12 AGENTS.md 目录结构段更新

回滚：base-ref 单 commit revert 即可（移动型 diff）。
