# Comet Design Handoff

- Change: autonomous-observability
- Phase: design
- Mode: compact
- Context hash: 2a136416fb16c91226bf7d8498c7007dd957611fe58469348402dd2a0140b4a7

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/autonomous-observability/proposal.md

- Source: docs/openspec/changes/autonomous-observability/proposal.md
- Lines: 1-44
- SHA256: 6958930b4b00929dece73346d48e8b97616e42fa04e16b61493e06ca4256668d

```md
---
comet_change: autonomous-observability
---

# autonomous-observability：自主运营看板与可观测性

## Why

自主运行批次 ④/④：前三个变更让链路能编排（①）、能回流（②）、敢无人值守（③），
但**运行状态只在后端**：流程有哪些、最近跑得怎样、有没有待人工确认的 blocked、
预算花到哪、熔断是否跳闸——用户看不到。没有可见性就不叫「托管给 agent」，
用户不会放心让它自己跑。

xiaobei 的做法是通过 IM 随时问、每日复盘推送；本批次不引入 IM（用户明确先不做），
改为**页面看板 + 状态端点**。

## What Changes

- 后端：`GET /api/flows/runs`（流程执行记录含逐步明细）+ 既有 `/api/autonomous/status`
  （熔断态/预算/blocked）与 `/api/feedback`（校准信号）已在 ②③ 交付
- 前端新增「自主运营」页（`AutonomousPage.tsx`，沿用 AutomationsPage 的设计体系）：
  流程列表（名称/步骤/调度/启用态）、新建（勾选五层步骤）、最近执行记录（逐步状态）、
  **待确认 blocked 清单**、熔断提示、当日预算用量
- 侧栏导航新增「自主运营」项
- E2E 新增 S13 场景（覆盖该页）；demo 新增第 6 段
- README 补「自主运营」章节

## Non-Goals

- **不做 IM 通道**（用户明确先不做）：看板与 API 即可见
- 不做告警推送（邮件/IM）：blocked 与熔断在页面可见，推送后续再议
- 不改护栏语义（②③ 已定）

## Capabilities

### New Capabilities

- `autonomous-observability`：自主运营状态在页面可见——流程、执行记录、待人工确认
  项、熔断态、预算用量一处可查

## Impact

`zimeiti_autonomous` 新增执行记录查询；前端新增一个页面与导航项；E2E 场景 12→13；
demo 5→6 段；README 增章。既有页面与任务行为零变化。

```

## docs/openspec/changes/autonomous-observability/design.md

- Source: docs/openspec/changes/autonomous-observability/design.md
- Lines: 1-53
- SHA256: 2bc151b233ce3eda3220aa435b3897b54d87607ccace84b8c75ab1d3a771e1c6

```md
---
comet_change: autonomous-observability
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：autonomous-observability

## 高层方案

```
后端（②③ 已有 + 本变更补一条）
  GET /api/flows/runs?flow_id=   执行记录含步骤明细（store.list_runs）
  GET /api/autonomous/status     熔断态 + 预算（③）
  GET /api/feedback              校准信号（②）

前端 AutonomousPage.tsx（沿用 AutomationsPage 范式）
  ① 流程列表（名称/步骤徽标/调度/启用态 + 停用/删除/立即执行）
  ② 新建面板（名称 + 五层步骤勾选 + 调度 + 主题/平台/仅草稿）
  ③ 执行记录（每次执行：状态、耗时、逐步明细）
  ④ 状态卡：待确认 blocked / 熔断提示 / 当日预算用量
侧栏导航新增「自主运营」；E2E S13；demo 第 6 段；README 章节
```

## 关键决策

### D1：样式严格克隆 AutomationsPage（教训驱动）
此前新增页面曾自造类名（.page/.form-row/.page-empty/裸 btn-primary）导致整页裸 HTML，
用户两次目检发现。本页**逐段对齐** AutomationsPage：
`.page-scroll` + `.page-head` + `h1.page-title` + `p.page-subtitle` + `.panel/.panel-title`
+ `.field-label/.field` + `.btn .btn-sm(.btn-primary/.btn-danger)` + `.badge` + `.card`
+ `.foot-note` + `.toast.ok/.toast-icon`。自定义 CSS 只用设计 token 且最少化。

### D2：执行记录查询走既有 store，不加新表
`flow_runs` + `flow_steps` 在 ① 已建；本变更只加读侧 `list_runs()`，JOIN 两步返回树形。

### D3：看板不做「立即执行真实链路」的默认按钮风险
立即执行会真实消耗 token。E2E/demo 用 mock；页面上按钮保留（用户显式点击才跑），
但 demo 脚本不点它（避免录制时烧钱）。

### D4：blocked 与熔断在页面显著位置
这两项是「无人值守」最需要人介入的信号，放在页面顶部状态卡而不是埋在列表里。

## 风险与对策

- **风险**：样式再次跑偏 → 构建后截图目检（表单态/列表态）并与既有页对比，写进验证报告
- **风险**：执行记录 JOIN 性能 → 限制返回条数（默认 20）与步骤截断
- **风险**：预算无单价（None）→ 页面如实显示「未折算」，不显示 0

## Open Questions

无。

```

## docs/openspec/changes/autonomous-observability/tasks.md

- Source: docs/openspec/changes/autonomous-observability/tasks.md
- Lines: 1-19
- SHA256: a489d5a31d8ae408d0888b2c0efd5c1701dfa9be28777b374dafdce3f3c55062

```md
---
comet_change: autonomous-observability
---

# Tasks：autonomous-observability

## 1. 后端执行记录

- [ ] 1.1 store.list_runs（flow_id 过滤 + 步骤明细）+ GET /api/flows/runs；单测 <!-- comet-task:668af003-d465-490b-816f-01aef2eed0fa -->

## 2. 前端看板

- [ ] 2.1 api.ts 类型与封装（flows/runs/status/feedback）+ AutonomousPage.tsx（严格克隆 AutomationsPage 范式 D1） <!-- comet-task:55185f22-f446-4c05-9cc7-1f3b99c74d45 -->
- [ ] 2.2 侧栏导航「自主运营」+ 路由挂载；构建 + 截图目检 <!-- comet-task:6cc45dc2-26b2-4fa8-92e8-e9c3f7ccc5b2 -->

## 3. 验证与文档

- [ ] 3.1 E2E 新增 S13 场景（zimeiti 独有 → parity NOTE）+ 全量 13 场景通过 <!-- comet-task:36781286-1074-440f-b278-39fc5f19bfc7 -->
- [ ] 3.2 demo 第 6 段录制 + README「自主运营」章节；make check 全绿 <!-- comet-task:96c2f510-7fe9-4b14-a4a3-faf276e45191 -->

```

## docs/openspec/changes/autonomous-observability/.openspec.yaml

- Source: docs/openspec/changes/autonomous-observability/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/autonomous-observability/specs/autonomous-observability/spec.md

- Source: docs/openspec/changes/autonomous-observability/specs/autonomous-observability/spec.md
- Lines: 1-41
- SHA256: abca191f20624aed504fb555b79b21cb5d9cad0cbd5f7dbd328231bd0b56d432

```md
# autonomous-observability 规格草案

## Purpose

让自主运营的状态在页面上可见：流程、执行记录、待人工确认项、熔断态、预算用量
一处可查，用户能放心把运营交给 agent。

## ADDED Requirements

### Requirement: 执行记录可查

系统 SHALL 提供 `GET /api/flows/runs`（可按 flow_id 过滤），MUST 返回每次执行的
状态、耗时与步骤级明细（步骤名、状态、耗时、错误）。

#### Scenario: 查询某流程的执行记录
- **WHEN** 调用 `GET /api/flows/runs?flow_id=<id>`
- **THEN** 返回该流程最近若干次执行，每次含步骤明细（含 blocked/failed 的步骤）

### Requirement: 自主运营页面

前端 SHALL 提供「自主运营」页面，MUST 展示流程列表与最近执行记录，并 MUST 展示
待确认（blocked）清单、熔断提示与当日预算用量；页面样式 MUST 沿用既有设计体系
（page-scroll / page-title / panel / field / btn / badge / card）。

#### Scenario: 看板可见四要素
- **WHEN** 用户打开「自主运营」页
- **THEN** 可见流程列表、执行记录、待确认项（或「无待确认项」）、预算用量
  （无单价时如实说明未折算）

#### Scenario: 新建流程勾选步骤
- **WHEN** 用户新建流程并勾选 discover/plan 两步、填名称与调度后保存
- **THEN** 流程出现在列表且步骤显示为所选子集

### Requirement: E2E 与文档

E2E SHALL 新增场景覆盖该页（记为 zimeiti 独有，easel 侧按预期差异 NOTE）；
README SHALL 新增「自主运营」章节说明编排/回流/护栏与看板。

#### Scenario: E2E 覆盖
- **WHEN** 运行全量 E2E
- **THEN** 场景数由 12 增至 13，全部通过且双端差异为 0（预期差异记 NOTE）

```
