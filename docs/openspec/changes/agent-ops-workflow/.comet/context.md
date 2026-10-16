# Comet Design Handoff

- Change: agent-ops-workflow
- Phase: design
- Mode: compact
- Context hash: 1dcafb8b0e09141ba78ab7504af90532315151491ae56846266b8ee902f9c01d

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/agent-ops-workflow/proposal.md

- Source: docs/openspec/changes/agent-ops-workflow/proposal.md
- Lines: 1-30
- SHA256: 24940535235684155bc2aa01cfa8d953a20130791ef253411ba2c86acf55d338

```md
---
comet_change: agent-ops-workflow
---

# agent-ops-workflow：五层运营流程技能化

## Why

OpenClaw→deepagents 迁移后，harness 层已对齐（文件工具/权限/PG 持久化），但 OpenClaw 时代的**五层运营流程知识**（发现/策划/制作/发布/归因）没有随之建模——agent 只有江小湖画像和通用提示词，做事靠即兴。实证：验证跑中 agent 自己报告「归因层没有数据支撑」「ai_score.py 没能跑」；同一选题两次生成走完全不同的路径。运营方法论散落在 multi-agent-manager 知识库与历史对话里，没有成为 agent 可按需读取的**结构化流程**。

## What Changes

- 新增五个内置 skills（`apps/skills/builtin/`）：`ops-discover`（发现=热点雷达选题）、`ops-plan`（策划=赛道评估/角度选择）、`ops-create`（制作=写作规范+质检清单）、`ops-publish`（发布=公众号草稿链路）、`ops-review`（归因=数据复盘）
- 每个 SKILL.md 定义：触发条件、执行步骤、数据源（系统 API/文件）、产物约定（落 outputs/）
- `agent_runtime.SYSTEM_PROMPT` 收敛为**索引 + 触发规则**：只声明五层存在与何时读哪个 skill，流程细节全部下沉到 SKILL.md（改流程不改代码）
- 归因层数据源接线：agent 可经文件系统读取 `_analytics/`（账号表现数据缓存），无数据时如实报告
- 用户问「做一期内容/发一篇/复盘」类请求时，agent 按 skill 流程执行并引用所在层

## Capabilities

### New Capabilities

- `agent-ops-workflow`：五层运营流程技能——agent 按发现/策划/制作/发布/归因五层执行运营任务，流程知识在 skills 中结构化沉淀

## Non-Goals

- 命令执行能力（agent-shell-exec，batch ②——质检/渲染脚本自动执行在那边做）
- 前端 OpenClaw 兼容债清理（frontend-openclaw-debt，batch ③）
- 多画像差异化流程（所有画像共用同一套五层流程）
- 发布动作自动化（发布层仍只产出草稿材料，不自动群发）

```

## docs/openspec/changes/agent-ops-workflow/design.md

- Source: docs/openspec/changes/agent-ops-workflow/design.md
- Lines: 1-52
- SHA256: 9477c8ce68563ed94db76d0b0508a8d3397eb099ab64e70750c8b6e4964aa4bd

```md
---
comet_change: agent-ops-workflow
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：五层运营流程技能化

## 高层方案

```
SYSTEM_PROMPT（索引层，改一次定型）
  "运营任务分五层：发现 ops-discover / 策划 ops-plan / 制作 ops-create /
   发布 ops-publish / 归因 ops-review。执行前必须先读对应 SKILL.md。"
        │ agent 按任务自选层
        v
apps/skills/builtin/ops-*/SKILL.md（流程层，可独立演进）
  每个文件声明：触发条件 → 执行步骤 → 数据源（API/文件）→ 产物约定 → 交接条件
        │ agent 用既有文件工具按需读取
        v
真实世界（已接线）
  发现层 ← /api/trends（热点雷达）
  策划层 ← 画像 profiles/（赛道/受众）+ 选题库 /api/ideas
  制作层 ← multi-agent-manager 写作规范（已沉淀为 WRITING 范式）
  发布层 ← wechat_mp draft.py（已沉淀，batch 外）
  归因层 ← outputs/_analytics/（本 change 新建最小数据源）
```

## 关键决策

### D1：skills 放 builtin 还是 shared
放 `apps/skills/builtin/`（与 card-design 等 119 个内置技能同层，/api/status 的技能清单自动收录，设置面板可见）。`shared/scripts/` 只放可执行脚本，不放流程文档。

### D2：归因层数据源——发布时写最小记录
系统当前没有持久化的往期表现数据（agent 实证报告过 `_analytics/` 不存在）。本 change 落**最小真实数据源**：发布流程（草稿创建成功）时在 `outputs/_analytics/` 追加一条 JSON 记录（日期、平台、内容路径、media_id、状态=pending-feedback），后续真实阅读/互动数据接入时在同一文件体系上扩展。归因层 SKILL.md 声明：读 `_analytics/`，无记录→如实报告。**不做**：接微信阅读数据 API（需要凭据+拉取任务，超出本 change）。

### D3：SYSTEM_PROMPT 收敛边界
索引化只删流程细节，保留既有硬约束（中文回复、文件布局说明、不编造数据）。触发规则用一句话×5 层，防止提示词膨胀。

### D4：制作层与 multi-agent-manager 知识库的关系
写作规范已在 case 中沉淀使用（WRITING 范式），制作层 SKILL.md 把它固化为**质检清单**（钩子/字数/格式/数据边界四项自检），不引入对 multi-agent-manager 仓库的运行时依赖（那是外部项目，知识要落在自己仓库）。

## 风险与对策

- **风险**：agent 不读 skill 直接即兴（prompt 遵从性）→ 对策：SYSTEM_PROMPT 用硬性指令（"必须先读"）+ 验证任务做对话探针确认
- **风险**：五层之间交接断裂（上层不知道下层产物在哪）→ 对策：每个 SKILL.md 显式写"交接条件"节，spec 已约束产物命名
- **风险**：归因层无数据被 agent 编造 → 对策：skill 明示"无记录即报告"，且 spec 场景覆盖

## Open Questions

无——三个关键决策（白名单执行器归 batch ②、五层 skills 载体、拆分方式）均已由用户确认。

```

## docs/openspec/changes/agent-ops-workflow/tasks.md

- Source: docs/openspec/changes/agent-ops-workflow/tasks.md
- Lines: 1-24
- SHA256: dd3074943d7d6bd505c8784291ce56ea5a7eebe714f9dd2a7ae521a154674aa9

```md
---
comet_change: agent-ops-workflow
---

# Tasks：五层运营流程技能化

## 1. 五层 skills 内容（apps/skills/builtin/）

- [ ] 1.1 `ops-discover/SKILL.md` 发现层：热点雷达（/api/trends 数据源）→ 热点筛选 → 收藏为选题（/api/ideas）；触发条件「发现选题/找热点/今天写什么」；产物=选题库条目
- [ ] 1.2 `ops-plan/SKILL.md` 策划层：读画像 profiles/（赛道/受众）评估选题契合度、产出差异化角度与推荐；触发条件「判断赛道/选角度/定选题」；交接条件=确定选题+角度后进制作层
- [ ] 1.3 `ops-create/SKILL.md` 制作层：按写作规范成稿（钩子/字数/格式/数据边界四项质检清单）；产物=outputs/ 下命名文章；触发条件「写文章/出初稿/做内容」
- [ ] 1.4 `ops-publish/SKILL.md` 发布层：草稿链路说明（wechat_mp draft 能力、只建草稿不发布）；产物=outputs/wechat-drafts/ 排版材料；交接条件=草稿创建成功后进归因层
- [ ] 1.5 `ops-review/SKILL.md` 归因层：读 outputs/_analytics/ 数据做结构化复盘；无记录时如实报告并说明需要什么数据；触发条件「复盘/数据怎么样」

## 2. Agent 接线

- [ ] 2.1 SYSTEM_PROMPT 索引化：五层名称+触发规则一句话+「执行前必须先读对应 SKILL.md」硬指令；删除流程细节（保留语言/文件布局/不编造数据等既有硬约束）
- [ ] 2.2 最小归因数据源：发布/草稿创建成功时写 `outputs/_analytics/` 记录（日期/平台/内容路径/media_id/状态），归因层读它

## 3. 验证

- [ ] 3.1 `make check` 全绿 + 浏览器 E2E S5（对话）无回归
- [ ] 3.2 对话探针：发「围绕某热点做一期内容」→ 验证 agent 按层执行（回复中明示流程层、引用 skill）；发「复盘」→ 无数据时如实报告
- [ ] 3.3 spec 场景核对：四条 Requirement 的 Scenario 逐条对照实现行为

```

## docs/openspec/changes/agent-ops-workflow/.openspec.yaml

- Source: docs/openspec/changes/agent-ops-workflow/.openspec.yaml
- Lines: 1-2
- SHA256: 9cfa2ab963a8c9b58eecdb9fd5b55544e988fee8de8b887226ffc32d27744459

```md
schema: spec-driven
created: 2026-10-16

```

## docs/openspec/changes/agent-ops-workflow/specs/agent-ops-workflow/spec.md

- Source: docs/openspec/changes/agent-ops-workflow/specs/agent-ops-workflow/spec.md
- Lines: 1-50
- SHA256: 1c2f8698e54307170044c44d86914e16bdd45574797166bb2784a603ddbfed09

```md
# agent-ops-workflow 规格草案

## Purpose

让运营 agent 具备结构化的五层运营流程：发现（热点→选题）、策划（赛道评估→角度）、制作（写作→质检）、发布（草稿链路）、归因（数据复盘）。流程知识以 skills 形式沉淀，agent 按需读取执行，使同类任务产出路径稳定、可审计、可独立演进。

## ADDED Requirements

### Requirement: 五层流程技能可被 agent 发现并按层执行

五个内置技能（发现/策划/制作/发布/归因）各自提供 SKILL.md，说明触发条件、执行步骤、数据源与产物约定；agent 系统提示词仅声明层级索引与触发规则，不含流程细节。

#### Scenario: 用户要求做一期内容
- **WHEN** 用户提出「围绕某热点做一期内容」类请求
- **THEN** agent 依次引用发现层与策划层 skill 执行选题与角度决策，并在回复中明示当前所处流程层
- **THEN** 全程未读任何一层 skill 而即兴产出的情况不出现

#### Scenario: 用户要求复盘已发内容
- **WHEN** 用户提出「复盘/看看数据」类请求
- **THEN** agent 引用归因层 skill，读取归因数据源并给出结构化复盘
- **THEN** 归因数据缺失时明确报告「无数据支撑」，不编造读数

### Requirement: 每层 skill 声明数据源与产物约定

每层 SKILL.md 必须声明：该层可用的系统数据源（API 端点或文件路径）、产物落盘位置（outputs/ 下）与命名约定、以及进入下一层的交接条件。

#### Scenario: 制作层产出可交接
- **WHEN** 制作层完成一篇文章
- **THEN** 产物落盘于内容库且命名符合约定，发布层可直接引用其路径继续
- **THEN** 产物缺失或命名不符时制作层不宣告完成

### Requirement: 归因层数据源接线

归因层 skill 声明的数据源必须在系统中真实存在：agent 能读到已发布内容的表现数据（来自系统既有账号分析数据），数据不存在时得到明确的「无数据」信号而非报错。

#### Scenario: 有数据时给复盘
- **WHEN** 归因数据源中存在目标内容的表现数据
- **THEN** agent 基于真实数据给出复盘结论，引用具体读数

#### Scenario: 无数据时如实报告
- **WHEN** 归因数据源为空或目标内容无记录
- **THEN** agent 明确报告无数据支撑，并说明需要什么数据才能复盘

### Requirement: 系统提示词只承载索引

系统提示词包含：五层名称、各自触发规则一句话、以及「执行前先读对应 skill」的硬性指令。任何流程步骤、话术模板、数据源细节不得写入系统提示词。

#### Scenario: 流程修改不需要改代码
- **WHEN** 运营者修改某一层的 SKILL.md（调整步骤或数据源）
- **THEN** 无需修改 agent 运行时代码，agent 下次对话即按新流程执行

```
