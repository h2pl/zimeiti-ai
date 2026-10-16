# Comet Design Handoff

- Change: agent-operating-contract
- Phase: design
- Mode: compact
- Context hash: ac5e7a64fbd2930a246146b2973ba755545fc1d7cb42391aca403fff289e5e72

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/agent-operating-contract/proposal.md

- Source: docs/openspec/changes/agent-operating-contract/proposal.md
- Lines: 1-36
- SHA256: e3bd81cadb938a2559720b0aa0d8428257337a49f02f4cc79f2d0eaa366079e8

```md
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

```

## docs/openspec/changes/agent-operating-contract/design.md

- Source: docs/openspec/changes/agent-operating-contract/design.md
- Lines: 1-54
- SHA256: 4d89ee31ce13909bb057e478119106cd6d18538d6f509655cab7847d8063f9d2

```md
---
comet_change: agent-operating-contract
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：操作契约层

## 高层方案

```
SYSTEM_PROMPT（重构为契约层，agent_runtime.py）
  ├─ 人格段（SOUL 凝练：沟通风格+做成心态）
  ├─ 执行偏向 + Promised Work + ask-first 分级（静态规则，照 OpenClaw 语义中文化）
  ├─ 编排 glue 接线（manifest/calendar_ops/output_paths 一句话纪律）
  ├─ 五层索引（① 已有，保留）
  └─ 【技能目录】动态注入段（_skills_catalog() 渲染，带缓存）
        │ get_skills()（已有 TTL 缓存）按 layer 分组
        ▼
ops-* SKILL.md ×5（退化为路由层）
  ├─ ops-discover → skill-trending-topics / skill-trend-rider
  ├─ ops-plan     → skill-topic-evaluator
  ├─ ops-create   → copywriting + skill-quality-gate
  ├─ ops-publish  → skill-wechat-publisher（+ content_guard / persona_gate / publish-log 门）
  └─ ops-review   → skill-publish-analytics / skill-content-postmortem
```

## 关键决策

### D1：技能目录注入——复用 get_skills 而非自建
`get_skills()` 已带 300s TTL 缓存、已产出 name/description/layer。在 SYSTEM_PROMPT 组装处调用一次渲染为分组清单（只放 name+description 一句，不放全文）。119 个技能 × ~40 字 ≈ 5KB，提示词增量可接受；若后续技能数暴涨再加「只注入当前任务相关层」的过滤。

### D2：静态契约 vs 动态事实的边界
人格/执行偏向/follow-through/ask-first 是**静态规则**（照 OpenClaw「prompt 不预拒绝、风险下沉运行时」的精神中文化）；技能目录/画像列表是**动态事实**（每次组装时渲染）。缓存边界对齐：静态段在前（稳定前缀），动态段在后（易变后缀）——OpenClaw 的 provider 缓存边界工程的简化版，Python 侧无 prompt cache API 故只做顺序。

### D3：ops-* 路由层的引用方式
每个 ops-* SKILL.md 保留「触发条件+本层职责一句话+必读详细技能清单（路径）+本层特有约定」。详细流程一律在既有技能里改——**本次不改动 114 个既有技能的内容**，只修引用关系。ops-publish 例外：发布门三步（content_guard→persona_gate→publish-log）写进 ops-publish，因为既有 skill-wechat-publisher 不含这些门。

### D4：付费确认复用 ask_human
不新增确认机制。ask-first 规则要求 agent 在调用付费媒体能力前用 ask_human（已有 HITL 中断+卡片）给出范围+预估。费用预估数据源：无（OpenClaw 也无 pre-call 估算——它只有事后 usage）。agent 按媒体类型给出「将调用 N 次生图」这类可确认的范围描述即可，不编造单价。

### D5：manifest/calendar/output_paths 的接入深度
只做「提示词纪律+ops-* 路由层点名」，不改造脚本本身。这三个脚本已在 skills/shared/scripts/（随库复制而来），先验证可运行（烟测），不可用则在对应 ops 技能里标注。

## 风险与对策

- **风险**：提示词膨胀导致指令遵循度下降 → 对策：静态段控制在 ~60 行内；技能目录只放 name+description；实施后用探针验证路由命中率
- **风险**：人格段与江小湖画像风格混淆 → 对策：人格段管 agent 沟通风格，明确写「内容风格以画像为准」
- **风险**：persona_gate/publish-log 脚本在库里但可能对不上我们的数据格式 → 对策：D5 烟测先行，不通则降级为「流程约定」并在 ops-publish 标注

## Open Questions

无（batch 决策已由用户确认：完整对齐、按需开启）。

```

## docs/openspec/changes/agent-operating-contract/tasks.md

- Source: docs/openspec/changes/agent-operating-contract/tasks.md
- Lines: 1-29
- SHA256: f8851b283af21417625336afbe5e3d627a111cb7bcab8c040fb677493f90d8e9

```md
---
comet_change: agent-operating-contract
---

# Tasks：操作契约层

## 1. 契约重构（agent_runtime）

- [ ] 1.1 SYSTEM_PROMPT 重构：人格段 + 执行偏向 + Promised Work + ask-first 分级 + 编排 glue 纪律 + 五层索引（保留）+ 技能目录动态注入段（get_skills 渲染，按 layer 分组，name+description） <!-- comet-task:1a0b50d3-40c3-4087-852e-b5f303d6be6f -->
- [ ] 1.2 技能目录注入带缓存（复用 get_skills 300s TTL；静态段在前动态段在后） <!-- comet-task:9339ed8d-f27c-4550-a994-d6cc7cf203b0 -->

## 2. ops-* 改路由层

- [ ] 2.1 ops-discover → skill-trending-topics/skill-trend-rider（保留触发词+层职责） <!-- comet-task:a99f0dea-da5f-4b5b-bf82-fb7043c3babb -->
- [ ] 2.2 ops-plan → skill-topic-evaluator <!-- comet-task:82531c47-7ab6-4908-bf79-b55a3bb64649 -->
- [ ] 2.3 ops-create → copywriting + skill-quality-gate <!-- comet-task:a59db007-98b3-47ea-bf6c-390436fc881f -->
- [ ] 2.4 ops-publish → skill-wechat-publisher + 发布门三步（content_guard → persona_gate 80 分线只提醒 → publish-log 留痕） <!-- comet-task:cf007ba9-a895-403e-be24-336a28d1a172 -->
- [ ] 2.5 ops-review → skill-publish-analytics / skill-content-postmortem <!-- comet-task:99cc4cf6-42d4-4cd9-a126-3f6eda00239b -->

## 3. glue 脚本烟测

- [ ] 3.1 manifest.py / calendar_ops.py / output_paths.py / persona_gate.py / publish-log 逐个烟测（存在且可运行）；不可用的在对应 ops 技能标注 <!-- comet-task:938fda43-1f1c-48ab-ad98-5e244343ca89 -->

## 4. 验证

- [ ] 4.1 探针 A：选题评估任务 → 路由到 skill-topic-evaluator 且先读 SKILL.md <!-- comet-task:febb4b3f-dc54-4219-a28a-f68787cceaca -->
- [ ] 4.2 探针 B：付费操作（生图）→ 触发 ask_human 确认而非直接执行 <!-- comet-task:ab6bba60-1894-4a64-89a9-34aa8437c57c -->
- [ ] 4.3 探针 C：清晰可逆任务（读画像）→ 直接执行不索求许可 <!-- comet-task:857a2004-0230-440a-9121-b55d54bf0316 -->
- [ ] 4.4 make check 全绿 + E2E S05 无回归 <!-- comet-task:3896b796-f873-452a-9f5a-9ff9f78ec673 -->

```

## docs/openspec/changes/agent-operating-contract/.openspec.yaml

- Source: docs/openspec/changes/agent-operating-contract/.openspec.yaml
- Lines: 1-2
- SHA256: 9cfa2ab963a8c9b58eecdb9fd5b55544e988fee8de8b887226ffc32d27744459

```md
schema: spec-driven
created: 2026-10-16

```

## docs/openspec/changes/agent-operating-contract/specs/agent-operating-contract/spec.md

- Source: docs/openspec/changes/agent-operating-contract/specs/agent-operating-contract/spec.md
- Lines: 1-75
- SHA256: 83bd49d124a123962079afacd386ec284d803c6d80510692de7504994f2e07ba

```md
# agent-operating-contract 规格草案

## Purpose

让 agent 具备可发现、可路由、有边界的操作契约：技能目录对 agent 可见且按路由链执行；执行有偏向（可逆即做）且有 follow-through 约束；风险按可逆性分级确认；编排 glue（manifest/calendar/output_paths）真实接线；发布走安全门；agent 有自己的人格与沟通风格。

## ADDED Requirements

### Requirement: 技能目录可发现且按路由链执行

系统提示词注入可用技能目录（名称+一句描述+路径），并声明路由纪律：先精确匹配任务层，无精确匹配复用最接近的，无相关才用通用能力；执行前必须 read 对应 SKILL.md。

#### Scenario: 任务路由到详细技能
- **WHEN** 用户要求「评估这个选题能不能做」
- **THEN** agent 从注入目录中定位策划层详细技能并先读其 SKILL.md 再执行（而非即兴或只用薄层概述）

#### Scenario: 无匹配时走通用能力
- **WHEN** 任务与任何技能均不相关
- **THEN** agent 用通用能力完成，且不虚构不存在的技能

### Requirement: 执行偏向与 follow-through

系统提示词包含执行偏向（有工具可用的请求即被授权，不在提示层预拒绝）与 Promised Work 约束（「正在查」是进度非完成；回合结束前必须安排完成或观察路径；禁止以计划/空壳文件冒充成品）。

#### Scenario: 可逆任务不索求额外许可
- **WHEN** 用户提出清晰且可逆的任务（如「读一下我的画像」）
- **THEN** agent 直接执行，不询问「我可以吗」

#### Scenario: 回合以真实产物收尾
- **WHEN** agent 在一轮中承诺了交付物
- **THEN** 回合结束时该交付物真实存在（落盘/已提交工具结果），或明确报告未完成的原因与下一步

### Requirement: ask-first 风险分级

动作按性质分级：清晰+可逆→直接执行；不可逆/外部可见/破坏性/隐私敏感/产生费用→先经 ask_human 说明范围与影响并获得确认。付费操作必须给出可得的费用预估。

#### Scenario: 付费操作先确认
- **WHEN** agent 需要调用产生费用的媒体生成能力（生图/生视频/音乐/TTS）
- **THEN** 先经 ask_human 给出操作范围与费用预估，用户确认后才执行

#### Scenario: 可逆任务不触发确认
- **WHEN** 任务是读取、草稿、本地可撤销修改
- **THEN** 不触发 ask_human 确认

### Requirement: 编排 glue 接线

跨层任务按契约使用编排脚本：规划/排期前读日历上下文（calendar_ops context --days 14）；跨层产物经 manifest 传递（路径+一句结论）；产物路径经 output_paths 校验后才写入。

#### Scenario: 排期前看日历
- **WHEN** agent 执行排期或内容规划
- **THEN** 先读取近 14 天日历上下文，避开已排内容

#### Scenario: 跨层产物有据可传
- **WHEN** 上游层产物交给下游层
- **THEN** 经 manifest 登记路径与结论，下游从 manifest 读取而非重新推导

### Requirement: 发布安全门

发布层流程内嵌：出站前 content_guard 扫描（BLOCK 级命中必须改稿）；人设一致性 persona_gate 检查（80 分线，只提醒不阻断，用户已明确要发布时继续）；发布后 publish-log 留痕。

#### Scenario: 人设门只提醒
- **WHEN** 发布内容人设评分低于 80
- **THEN** agent 展示分数、偏离点与建议，但不阻断已确认的发布

#### Scenario: 发布后留痕
- **WHEN** 草稿创建成功
- **THEN** publish-log 记录平台/标题/画像，供归因层读取

### Requirement: agent 人格段

系统提示词包含 agent 自身的人格与沟通风格段（凝练自 SOUL.md）：先想「怎么帮他做成」而非「我做不了」；清晰坦诚，卡住时说明原因与替代路径；聚焦运营场景不做无关闲聊。

#### Scenario: 遇障碍给替代路径
- **WHEN** agent 遇到工具或数据障碍
- **THEN** 回复说明卡点并给出可行的替代路径，而非仅报告失败

```
