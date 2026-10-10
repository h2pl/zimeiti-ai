# Comet Design Handoff

- Change: web-workbench
- Phase: design
- Mode: compact
- Context hash: 3df859ee44e5ab37aa1011c2bddf6f26d96263cd78e3ee322018815a8e4ee408

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/web-workbench/proposal.md

- Source: openspec/changes/web-workbench/proposal.md
- Lines: 1-42
- SHA256: f29e120d3f577df0ef0f4f226c756885300687342311cb13e339cc5709c9017c

```md
# 提案：Web 运营工作台（web-workbench）

## Why

Web 前端目前是单文件 `App.tsx`（审批/看板/日历挤在一个页面，无路由无导航），
对照参考项目 Easel 的 `web/frontend`（React 多页工作台：Dashboard/Chat/Accounts/
Profile/Outputs/Publish/Calendar/Ideas/Trends/Skill 十页）差距明显——托管形态的
「人在环」入口需要结构化页面承载，散装区块无法支撑多账号日常运营。

## What Changes

- **前端（apps/web）**：引入 react-router-dom 多页路由 + 侧边栏布局（对标 Easel），
  拆分并新增 7 个页面：概览 Dashboard / 审批中心 Approvals（含问题卡片）/
  选题看板 Ideas / 内容日历 Calendar / 画像管理 Profile / 趋势 Trends /
  内容库 Outputs；统一 `api/` 客户端模块
- **后端（apps/api）**：新增 4 组只读+受控写端点：
  - `GET /api/dashboard`（待审批数/账号启停/今日发布/最近日志）
  - `GET /api/profiles`、`GET/PUT /api/profiles/{account}`（画像查看与编辑，
    PUT 经 validate_profile fail-closed 校验）
  - `GET /api/trends/{account}`（复用校准证据引擎的基线归一化指标）
  - `GET /api/outputs/{account}`（内容库：已发布草稿产物清单）
- 现有审批/提问/看板/日历端点与行为不变（前端重组消费）

## Capabilities

- **New Capabilities**: `web-workbench`（工作台页面结构与数据端点行为）
- **Modified Capabilities**: 无（既有端点契约不变，仅新增）

## Non-Goals

- 不做 Agent 聊天页（Easel ChatPage 对标需要新的会话端点与流式协议，
  独立变更；托管审批已覆盖现有人机交互）
- 不做多平台发布中心 UI（Easel PublishPage 对标——发布走 agent+审批闭环，
  人工手发入口待 PRD 扩展）
- 不做账号登录 UI（平台登录走既有扫码/凭证链路）
- 不改发布/校准/网关等后端行为

## 关键决策

- 路由用 react-router-dom（Easel 同款形态）；构建验证纳入 `pnpm build`（tsc 严格）
- 画像编辑是**受控写**：只写 `profiles/<account>/profile.yaml`（git 追踪，可 diff 可回滚）
- 趋势数据 100% 复用 `operations.calibration.build_evidence`（不重写统计逻辑）

```

## openspec/changes/web-workbench/design.md

- Source: openspec/changes/web-workbench/design.md
- Lines: 1-41
- SHA256: 50786f86bfd6a76dc54b55c54366ca8200600fcfd65f073ed9d64732bc827180

```md
---
comet_change: web-workbench
role: technical-design
canonical_spec: openspec
---

# 设计：web-workbench

## Context

apps/web 现状：单 `App.tsx`（审批+看板+日历+日志四区块，5s 轮询）、vite 代理
`/api → :8000`、pnpm 构建。后端已有端点：approvals/questions/kanban/calendar/
publish-log；缺 dashboard/profiles/trends/outputs。参考 Easel `web/frontend/src/`
（App.tsx 路由 + components/ 页面组件）与本项目「顶层组装器」惯例。

## Goals / Non-Goals

- Goals：路由化多页工作台、后端数据端点齐备、行为有规格有测试
- Non-Goals：聊天页、发布中心 UI、账号登录 UI（见 proposal Non-Goals）

## 决策记录

- **D1 路由选型 react-router-dom**：Easel 同款生态；新增依赖仅此一个。
  `App.tsx` 变为 Layout+Routes 组装器，页面组件拆 `src/pages/`。
- **D2 API 客户端集中**：`src/api.ts` 统一 fetch 封装（类型化返回），页面不直接
  fetch——轮询/错误处理单点维护。
- **D3 画像编辑 fail-closed**：PUT 端点服务端 `validate_profile` 校验通过才写
  `profiles/<account>/profile.yaml`；写入即 git 追踪文件变更（自用期可 diff 回滚，
  不做草稿/撤销 UI）。目录遍历防护：account 参数白名单校验（`^[A-Za-z0-9_-]+$`）。
- **D4 趋势复用证据引擎**：`GET /api/trends/{account}` 直接调
  `operations.calibration.build_evidence` 返回 baseline 字段，不新写统计。
- **D5 内容库只读扫描**：`GET /api/outputs/{account}` 扫
  `OUTPUTS_DIR/<account>/*/drafts.json` 的元数据（slug/标题/合规/created_at），
  account 参数同样白名单校验，不读正文（防路径注入与超大响应）。
- **D6 构建验证**：`pnpm build`（tsc -b + vite build）纳入变更验证证据；
  make check 维持 api 侧不变。

## 风险

- 画像 PUT 是全仓唯一受控写端点：路径白名单 + validate 双保险（D3）
- tsc 严格模式下现有 App.tsx 代码需过类型检查（已验证 `npx tsc --noEmit` 通过）

```

## openspec/changes/web-workbench/tasks.md

- Source: openspec/changes/web-workbench/tasks.md
- Lines: 1-22
- SHA256: 24d984ce60fe911d118d1536e40635db5bdde7340b7c5a9d81c979f65d51cc02

```md
# 任务：web-workbench

## 1. 后端端点

- [ ] T1 `GET /api/dashboard`：待审批数/账号启停/今日发布数/最近日志 + 测试 <!-- comet-task:2c863dd4-8ade-4b32-9cde-fb16c551be4b -->
- [ ] T2 `GET /api/profiles` + `GET/PUT /api/profiles/{account}`（validate_profile <!-- comet-task:b071bdf4-d6a6-4508-ad3b-24ffe3ca27d3 -->
      fail-closed + account 白名单防路径遍历）+ 测试
- [ ] T3 `GET /api/trends/{account}`（复用 build_evidence）+ `GET <!-- comet-task:b5c8c120-e540-4058-b761-d10e7f69a9fc -->
      /api/outputs/{account}`（只读元数据扫描）+ 测试

## 2. 前端路由化

- [ ] T4 引入 react-router-dom；App.tsx 改 Layout（侧边栏导航）+ Routes <!-- comet-task:53af429a-26e0-4f1c-9d5b-29da24593523 -->
- [ ] T5 `src/api.ts` 类型化客户端；Approvals/Ideas/Calendar 页面从现 App.tsx 拆出 <!-- comet-task:43dfdadf-293c-4115-b5db-af1732079320 -->
- [ ] T6 Dashboard / Profile / Trends / Outputs 四个新页面（消费新端点） <!-- comet-task:934929e1-2771-4c34-a5e5-772a395255aa -->
- [ ] T7 `pnpm build` 通过（tsc 严格） <!-- comet-task:703e5394-d82c-48ba-abee-1533340ddd86 -->

## 3. 验证与收尾

- [ ] T8 make check 全绿（后端新增测试计入） <!-- comet-task:ec03c37e-90a6-4274-ab4a-df63a2b77b80 -->
- [ ] T9 入口冒烟：vite dev 起服 + 关键 API 返回 200；pnpm build 证据 <!-- comet-task:4930c6a5-f6ad-4112-858e-8d06569e8b88 -->
- [ ] T10 spec 场景核对（5 需求 6 场景逐条对照实现与测试） <!-- comet-task:76f47c71-d8d2-4edd-884a-fb0d8273a4cc -->

```

## openspec/changes/web-workbench/.openspec.yaml

- Source: openspec/changes/web-workbench/.openspec.yaml
- Lines: 1-2
- SHA256: e61703315c59969805e021ec521ca189369aaf8ea902d52c5e39c7fbc603598f

```md
schema: spec-driven
created: 2026-10-10

```

## openspec/changes/web-workbench/specs/web-workbench/spec.md

- Source: openspec/changes/web-workbench/specs/web-workbench/spec.md
- Lines: 1-47
- SHA256: 1b74e5ad7f143f64f84834b40028dff0fb94e0d5096b2bea26f1e25b7e81f0dd

```md
# web-workbench 能力增量

## ADDED Requirements

### Requirement: 侧边栏路由导航

工作台提供侧边栏导航，覆盖全部页面；直接访问子路径可渲染对应页面。

#### Scenario: 未审批时访问概览
- **When** 用户访问 `/`
- **Then** 概览页渲染，显示待审批数、账号启停状态、今日发布数与最近日志

### Requirement: 审批中心

审批中心页展示待审批项（确认/拒绝）与 agent 提问卡（选项按钮+自定义回答），
行为与既有 API 一致。

#### Scenario: 多轮双闸门审批
- **When** 恢复执行命中下一个中断并重登记 pending
- **Then** 审批中心在 5s 轮询内出现新待审批卡片

### Requirement: 画像查看与编辑

画像页列出全部账号；可查看与编辑指定账号画像；PUT 提交经 validate_profile
校验，非法输入返回 400 且不落盘。

#### Scenario: 非法画像编辑被拒绝
- **When** PUT `/api/profiles/{account}` 提交缺少必填字段的画像
- **Then** 返回 400，`profiles/<account>/profile.yaml` 内容不变

### Requirement: 趋势基线归一化

趋势页展示指定账号的账号级指标均值/最新值/归一化倍率，数据来自校准证据引擎
（只读）。

#### Scenario: 无数据账号展示降级提示
- **When** 账号无任何快照
- **Then** 趋势页展示「无数据」而非零值

### Requirement: 内容库

内容库页列出指定账号已发布的草稿产物（slug、标题、合规结论、创建时间），
只读。

#### Scenario: 空内容库
- **When** 账号无产物目录
- **Then** 内容库页展示空态而非报错

```
