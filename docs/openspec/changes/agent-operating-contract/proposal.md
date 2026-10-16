---
comet_change: agent-operating-contract
---

# agent-operating-contract：操作契约层对齐 OpenClaw

## Why

对照 OpenClaw 源码（npm openclaw@2026.10.2，238MB dist）与 Easel 的 AGENTS.md/SOUL.md 系统调研，我们的 harness 缺的不是技能（119 个同源），而是**操作契约层**——OpenClaw 每次运行自建系统提示，含 18 个固定小节（Execution Bias / Promised Work / Skills / Tooling 等），我们只有静态四段。实证缺口：

- **技能目录未注入**：探针证实 agent 只用 ops-* 薄版，库里 skill-topic-evaluator（143 行七维深评）等 114 个详细技能完全不被路由——`<available_skills>` 注入 + 模型按需 read 是 OpenClaw 的核心机制
- **无执行偏向**：agent 过度谨慎（「穷尽路径后不敢动」的旧事故现场即此形态）；OpenClaw 明令「有工具可用的请求即被授权，风险由运行时门禁把关，prompt 不预拒绝」
- **无 Promised Work**：无「说我在查了≠完成 / 回合结束前安排完成路径」的 follow-through 约束——虚拟 FS 时代 agent 声称「已保存」但磁盘无文件正是此缺口
- **发布门未接线**：content_guard 已入 exec 注册表，但 persona_gate（人设 80 分线）与发布留痕（publish-log）不在流程里
- **编排 glue 闲置**：manifest.py（产物传递）/calendar_ops.py（排期前读日历）/output_paths.py（路径门禁）脚本都在库里，提示词零引用，agent 靠口头传递跨层产物
- **无 agent 人格**：SOUL.md 管 agent 自己的沟通风格与心态（「先想怎么做成」），画像 style.md 只管内容风格

## What Changes

- **SYSTEM_PROMPT 重构**为契约层：技能目录动态注入（name+description+路径，按 layer 分组）+ 路由链纪律（精确→最接近→通用）+ Execution Bias + Promised Work + ask-first 分级（清晰可逆直接做；不可逆/外部/破坏性/隐私敏感/付费先问）+ 编排 glue 接线（manifest 传递/calendar context/output_paths 校验）+ 行为边界（先查再问、不每次都出 Plan、真实产物才算完成）
- **ops-* 五个 SKILL.md 改为路由层**：指向对应详细技能（ops-plan→skill-topic-evaluator、ops-create→copywriting/skill-quality-gate、ops-publish→skill-wechat-publisher、ops-discover→skill-trending-topics/skill-trend-rider、ops-review→skill-publish-analytics/skill-content-postmortem），消除平行重复
- **发布门接线**：ops-publish 流程内嵌 content_guard scan（已有）+ persona_gate check（80 分线，只提醒不阻断）+ publish-log 留痕
- **SOUL 人格段**：凝练进 SYSTEM_PROMPT（沟通风格+「先想怎么做成」心态），不含 Easel 特有渠道描述

## Capabilities

### New Capabilities

- `agent-operating-contract`：agent 操作契约——技能目录可发现且按路由链执行、执行偏向与 follow-through 约束、ask-first 风险分级、编排 glue 接线、发布安全门、agent 人格

## Non-Goals

- 记忆五层架构（batch ② agent-memory-system）
- 模型 fallback 链 / cron 定时 / 成本统计（batch ③ model-resilience-cron）
- exec 审批的身份绑定（realpath+哈希）与 Lobster 工作流
- OpenClaw 的 channel 层（多渠道路由）——单用户工作台不需要
