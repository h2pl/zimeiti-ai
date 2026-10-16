---
change: agent-operating-contract
design-doc: docs/openspec/changes/agent-operating-contract/design.md
base-ref: 5a52fe1
---

# Plan：操作契约层

<!-- comet-task-authority: docs/openspec/changes/agent-operating-contract/tasks.md -->

## G1 契约重构 <!-- comet-task-ref:1a0b50d3-40c3-4087-852e-b5f303d6be6f --><!-- comet-task-ref:9339ed8d-f27c-4550-a994-d6cc7cf203b0 -->

SYSTEM_PROMPT → _CONTRACT_HEAD（人格/执行偏向/Follow-through/ask-first/编排纪律/
五层索引/文件系统/白名单脚本/语言）+ _skills_catalog()（get_skills 渲染按 layer 分组）+
build_system_prompt()；_build_agent 改用组装函数。

## G2 ops-* 路由层 <!-- comet-task-ref:a99f0dea-da5f-4b5b-bf82-fb7043c3babb --><!-- comet-task-ref:82531c47-7ab6-4908-bf79-b55a3bb64649 --><!-- comet-task-ref:a59db007-98b3-47ea-bf6c-390436fc881f --><!-- comet-task-ref:cf007ba9-a895-403e-be24-336a28d1a172 --><!-- comet-task-ref:99cc4cf6-42d4-4cd9-a126-3f6eda00239b -->

五个 SKILL.md 重写为路由层（触发词+层职责+必读详细技能路径+交接）；ops-publish
内嵌发布门三步；不改动 114 个既有技能内容。

## G3 glue 烟测 <!-- comet-task-ref:938fda43-1f1c-48ab-ad98-5e244343ca89 -->

manifest/calendar_ops/output_paths/persona_gate --help 烟测。

## G4 验证 <!-- comet-task-ref:febb4b3f-dc54-4219-a28a-f68787cceaca --><!-- comet-task-ref:ab6bba60-1894-4a64-89a9-34aa8437c57c --><!-- comet-task-ref:857a2004-0230-440a-9121-b55d54bf0316 --><!-- comet-task-ref:3896b796-f873-452a-9f5a-9ff9f78ec673 -->

三探针（路由/付费确认/可逆直做）+ make check + S05。
