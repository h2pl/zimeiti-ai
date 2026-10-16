# Comet Design Handoff

- Change: ops-console-ui
- Phase: design
- Mode: compact
- Context hash: 63e469ca6e29e494024ffed48975cf730f0066705b42ed3a53a4cb01d6ab9bc1

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/ops-console-ui/proposal.md

- Source: docs/openspec/changes/ops-console-ui/proposal.md
- Lines: 1-44
- SHA256: cc4dde757a4bf14e766e29ae3d9eae2aa9a2e7968d354b194cc1b02cac297925

```md
---
comet_change: ops-console-ui
---

# ops-console-ui：运营控制台（定时任务 + 用量统计）

## Why

前两个批次把后端能力补齐了，但**用户看不见也配不了**：

- `/api/automations`（定时任务的增删改查、立即执行、执行记录）**无任何前端引用**
  ——想「每天早上自动出稿」只能调 API 或改环境变量
- `/api/usage`（会话 token 统计）同样无 UI——不知道哪轮对话吃了多少 token
- `ZIMEITI_FALLBACK_MODELS`（模型 fallback 链）、`ZIMEITI_SUBAGENT_MODEL`（子代理模型）
  只能改环境变量，设置面板不可配

对照 OpenClaw：它的定时/用量/模型配置都在控制台可见可改。我们后端已就位，缺的是产品面。

## What Changes

- **新增「自动化」页**（侧栏导航项）：定时任务列表（名称/类型/时刻/下次运行/开关）、
  新建（名称+类型+每日时刻+指令）、立即执行、删除、最近执行记录（状态+摘要+耗时）
- **用量概览**：工作台新增用量卡片（近 30 天 prompt/completion token 汇总），
  设置面板展示按模型/会话的明细
- **设置面**：fallback 链与子代理模型在设置面板可见（只读展示当前环境变量取值 +
  如何修改的说明）——不提供写入（避免误改运行时环境变量造成不一致）

## Non-Goals

- cron 表达式（后端只支持每日 HH:MM，UI 不超前）
- 用量金额换算（无单价数据，只展示 token）
- 定时任务的执行日志全文查看（只展示摘要，全文在 outputs/_automations/）
- 后端改动（端点已齐）

## Capabilities

### New Capabilities

- `automations-console`：定时任务在 UI 可见可管（列表/新建/开关/立即执行/删除/执行记录）
- `usage-observability`：会话用量在 UI 可查（汇总卡片 + 明细）

## Impact

前端新增 1 个页面组件 + 1 个用量卡片；侧栏新增 1 个导航项；无后端改动。

```

## docs/openspec/changes/ops-console-ui/design.md

- Source: docs/openspec/changes/ops-console-ui/design.md
- Lines: 1-51
- SHA256: 89226fbcae181b90f22eeb517b5f7165ba511a0312c9067f143cd0f73f6f273d

```md
---
comet_change: ops-console-ui
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：运营控制台（定时任务 + 用量统计）

## 高层方案

```
Sidebar NAV += { page: 'automations', Icon: IconAutomations, label: '自动化' }
App.tsx      renderPage: case 'automations' → <AutomationsPage />
components/AutomationsPage.tsx  ← 新建（列表/新建表单/开关/立即执行/删除/执行记录）
components/UsageCard.tsx        ← 汇总卡片（工作台 + 设置面板复用）
lib/api.ts   += listAutomations/createAutomation/updateAutomation/deleteAutomation/
                runAutomationNow/listAutomationRuns/getUsage
```

## 关键决策

### D1：复用既有页面范式，不引入新依赖
现有页面（IdeasPage/OutputsPage）用 `fetch` + `useState/useEffect` 直连 `/api/*`，
无 react-query 等。新页面沿用同款写法（含 loading/error/empty 三态），与代码库一致。

### D2：「立即执行」不等待完成
后端 `run-now` 已是后台任务（立即返回 `{ok, started}`）。UI 点击后**提示已提交**，
并在 2 秒后刷新执行记录——不轮询阻塞、不假装同步完成（case 任务要跑几分钟）。

### D3：用量只展示 token，不折算金额
无单价数据源；界面标注「仅统计 token，未折算费用」，避免和契约里
「没有单价数据就说明将调用的次数与规格，不要编造金额」相冲突。

### D4：环境变量类配置**只读展示**
fallback 链 / 子代理模型是进程环境变量，改 UI 不会生效（除非重启且来源一致）。
设置面板只展示当前取值与修改方式说明——展示「假的可编辑控件」比不做更糟。

### D5：时刻输入用 HTML time input + 后端校验兜底
前端 `<input type="time">` 天然限制 HH:MM；后端仍校验（25:99 拒绝）——
两端校验不互相替代（后端是权威）。

## 风险与对策

- **风险**：自动化页在后端不可达时白屏 → 三态处理 + try/catch
- **风险**：用量表为空时展示怪异 → 明确空态文案「暂无用量数据」
- **风险**：新增导航项挤占侧栏 → 侧栏现有 6 项，加 1 项仍在可读范围

## Open Questions

无。

```

## docs/openspec/changes/ops-console-ui/tasks.md

- Source: docs/openspec/changes/ops-console-ui/tasks.md
- Lines: 1-25
- SHA256: 57b119b5b08d199d0c3d8e46a810420f260cd928b07b0867e4960c4079a417bf

```md
---
comet_change: ops-console-ui
---

# Tasks：运营控制台（定时任务 + 用量统计）

## 1. API 封装

- [ ] 1.1 `lib/api.ts` 补 automations 与 usage 六个函数（列表/新建/更新/删除/立即执行/执行记录/用量） <!-- comet-task:a2d50993-6cd0-48b5-b4d7-c4cd44b10966 -->

## 2. 自动化页

- [ ] 2.1 `components/AutomationsPage.tsx`：任务列表（名称/类型/时刻/下次运行/开关）+ 三态（loading/error/empty） <!-- comet-task:9c1ff0a5-8ba7-4d7b-8fb6-986695bc71fd -->
- [ ] 2.2 新建表单（名称+类型+时刻+指令）+ 后端错误提示（非法时刻/prompt 缺指令） <!-- comet-task:0ba93751-7b95-4122-aea1-61d5c0985090 -->
- [ ] 2.3 立立执行（后台提交提示 + 延迟刷新）+ 执行记录区（状态/摘要/耗时）+ 删除 <!-- comet-task:feaf9de8-9dd3-4e31-bd4c-8ef21ead0ff9 -->

## 3. 用量概览

- [ ] 3.1 `components/UsageCard.tsx`：汇总卡片（近 30 天 prompt/completion）+ 明细行 + 空态 <!-- comet-task:75b77b78-77fd-42d4-9867-d03a043623fc -->
- [ ] 3.2 接入工作台与设置面板；fallback 链/子代理模型只读展示 <!-- comet-task:d283e83e-c88c-41ee-af48-8e30d5d6012e -->

## 4. 导航与验证

- [ ] 4.1 侧栏加导航项 + App.tsx 路由分支 + 图标 <!-- comet-task:ef42909e-a35f-4121-9f30-593cf7c2c990 -->
- [ ] 4.2 tsc 通过 + make check 全绿 + 浏览器实测（新建→立即执行→记录出现→删除） <!-- comet-task:42d1827c-262e-41a2-a0b3-4383fb2c36f4 -->

```

## docs/openspec/changes/ops-console-ui/.openspec.yaml

- Source: docs/openspec/changes/ops-console-ui/.openspec.yaml
- Lines: 1-2
- SHA256: 4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9

```md
schema: spec-driven
created: 2026-10-17

```

## docs/openspec/changes/ops-console-ui/specs/ops-console-ui/spec.md

- Source: docs/openspec/changes/ops-console-ui/specs/ops-console-ui/spec.md
- Lines: 1-38
- SHA256: 3a5000b02909c335de47b34a715f8e17f3694c526762ab730bf56380a3723249

```md
# ops-console-ui 规格草案

## Purpose

让已建成的后端运营能力（定时任务、用量统计）在界面上可见可管，让用户不必调 API 或改环境变量就能配置「每天自动出稿」并看到 token 消耗。

## ADDED Requirements

### Requirement: 定时任务在界面可见可管

用户可在「自动化」页查看、新建、启停、立即执行、删除定时任务，并看到最近执行记录；操作反映后端真实状态。

#### Scenario: 查看任务列表
- **WHEN** 用户进入自动化页
- **THEN** 展示全部任务（名称/类型/每日时刻/下次运行/启用开关）；无任务时给出空态说明（如何新建）；读取失败时显示错误而不是空白

#### Scenario: 新建每日任务
- **WHEN** 用户填写名称、选择类型（case/prompt）、填写每日时刻（HH:MM）与指令并提交
- **THEN** 任务创建成功并出现在列表，下次运行时间可见
- **THEN** 时刻非法（如 25:99）或 prompt 类缺指令时，界面显示后端返回的错误原因

#### Scenario: 立即执行与执行记录
- **WHEN** 用户对某任务点「立即执行」
- **THEN** 请求立即返回（后台执行，不阻塞界面），执行记录中出现该次运行（状态/摘要/耗时）
- **THEN** 记录可刷新查看最新状态

#### Scenario: 启停与删除
- **WHEN** 用户切换开关或删除任务
- **THEN** 后端状态随之更新，界面同步

### Requirement: 用量在界面可查

用户可看到近期 token 消耗汇总与按会话/模型的明细；无数据时如实展示为空。

#### Scenario: 查看用量
- **WHEN** 用户打开工作台或设置中的用量区
- **THEN** 展示所选区间（默认近 30 天）的 prompt/completion token 汇总与明细行
- **THEN** 无用量数据时展示「暂无数据」，不显示 0 之外的编造值

```
