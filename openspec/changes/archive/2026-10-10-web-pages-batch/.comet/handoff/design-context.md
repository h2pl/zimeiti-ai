# Comet Design Handoff

- Change: web-pages-batch
- Phase: design
- Mode: compact
- Context hash: f1f13d33e396c1bd6aa7f69ecbfbfcabbc185fe770ed9f5a2ddfb79054c40cb0

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/web-pages-batch/proposal.md

- Source: openspec/changes/web-pages-batch/proposal.md
- Lines: 1-45
- SHA256: b27d718221e26923265676e0095cf7b7e82d57c3af8a8ef02d7dd829f86a8be3

```md
# 提案：Easel 页面对齐第二批（web-pages-batch）

## Why

「全部照抄 Easel 前端页面」需求的第一批（web-workbench + web-easel-alignment）
覆盖了设计系统与 8 个页面，但 Easel 完整页面清单中仍有 4 页缺失：AccountsPage
（账号管理）、BreakdownPage（拆爆款/单篇复盘）、SkillPage（技能/运维操作）、
SettingsPanel（设置）。本变更补齐这四页及其后端端点。

## What Changes

- 后端（apps/api）：
  - `GET /api/accounts`：账号管理数据（画像账号 × 启停状态 × 凭证存在 × 登录态文件）
  - `POST /api/accounts/{account}/toggle`：启停切换（governance.platform_state）
  - `GET /api/postmortems/{platform}`：单篇复盘清单（复用 postmortem.top_formula）
  - `GET /api/postmortems/{platform}/{title}`：单篇复盘证据 + markdown
  - `GET /api/settings` / `PUT /api/settings`：webhook URL 等运行时设置
    （读写 data/state/settings.json；webhook 写入后即时生效于 notify）
  - `GET /api/tools`：agent 工具清单（名称+描述，来自 build_default_tools）
- 前端（apps/web）：
  - AccountsPage：账号卡片（启停切换/凭证状态/登录态状态）
  - BreakdownPage：复盘列表 + 单篇证据页（markdown 渲染）
  - SkillPage：运维操作（触发托管循环/立即取数/立即校准——写触发标记文件由网关消费）+ agent 工具清单展示
  - SettingsPage：通知 webhook 配置 + 主题切换入口

## Capabilities

- **New Capabilities**: 无（页面与端点为 web-workbench 能力域的扩展，规格并入
  `specs/web-workbench/spec.md` 的 MODIFIED 增量）

## Modified Capabilities

- `web-workbench`：新增账号管理/复盘/设置/运维操作四组端点与页面需求

## Non-Goals

- ChatPage（agent SSE 会话）与 PublishPage（发布中心）：独立变更（web-chat-publish）
- OnboardingWizard 引导流程
- 平台登录 UI（扫码仍走既有链路）

## 关键决策

- 运维操作（触发托管循环/取数）采用**触发标记文件**模式（data/state/ops-trigger.json），
  由常驻网关调度器每次循环消费——避免 API 进程与网关进程的并发执行冲突
- Breakdown 的 markdown 渲染引入 marked + dompurify（Easel 同款两个运行时依赖）

```

## openspec/changes/web-pages-batch/design.md

- Source: openspec/changes/web-pages-batch/design.md
- Lines: 1-39
- SHA256: fb084b57062e4c8f2e29d8a855b22b4a125d9d4c57a81d5c9e5061fe5ab586ac

```md
---
comet_change: web-pages-batch
role: technical-design
canonical_spec: openspec
---

# 设计：web-pages-batch

## Context

web-workbench 已交付 8 页；本批补 Easel 页面清单中的 Accounts/Breakdown/
Skill（运维）/Settings 四页。后端已有可复用资产：governance.platform_state
（启停）、operations.postmortem（复盘证据）、core.notify（webhook）、
operations.workbench（账号列表）。缺口是：凭证/登录态存在性探针、复盘端点化、
设置持久化、运维触发机制、前端四页。

## Goals / Non-Goals

- Goals：四页 + 端点 + 测试；运维触发经标记文件由网关消费
- Non-Goals：ChatPage/PublishPage（独立变更 web-chat-publish）；Onboarding；平台登录 UI

## 决策记录

- **D1 账号管理数据面**：`operations/workbench.py` 增 `accounts_detail()`——
  聚合 profiles 账号 × platform_state 启停 × `data/credentials/<a>.sealed`
  存在性 × `data/login/xhs_state.json` 存在性。toggle 端点调
  `platform_state.set_enabled`（复用既有 fail-closed 语义），account 白名单校验同 D3。
- **D2 复盘端点化**：直接调 `operations.postmortem` 的 `top_formula`/
  `note_evidence`（不重写）；渲染交给前端（返回结构化 JSON 而非 md 文本）。
- **D3 设置持久化**：`core/settings.py`——`data/state/settings.json`
  （{notify_webhook_url}），get/set 带容错；notify.py 改为每次发送时读设置
  （env 优先级高于设置文件，保持向后兼容）。
- **D4 运维触发标记文件**：`data/state/ops-trigger.json`（{"hosted_daily": ts,
  "ops_daily": ts}）；SkillPage POST 写标记，网关 `scheduler_loop` 每轮检查
  标记并执行对应任务后清除。API 与网关可能不同进程——标记文件是唯一安全通道。
- **D5 agent 工具清单**：`runtime/tools.py` 导出 `tool_catalog()`——从
  build_default_tools 的工具名+description 生成（不含闭包执行），只读展示。
- **D6 前端 markdown**：BreakdownPage 渲染复盘文本引入 marked+dompurify
  （Easel 同款两依赖）。

```

## openspec/changes/web-pages-batch/tasks.md

- Source: openspec/changes/web-pages-batch/tasks.md
- Lines: 1-23
- SHA256: 68c904cea9db3f54a5e45812d1fed1fd701554679dcc53dcf45fc8ebd53e0e78

```md
# 任务：web-pages-batch

## 1. 后端

- [ ] T1 `core/settings.py`：get/set 运行时设置（notify webhook 即时生效）+ 测试
- [ ] T2 `operations/workbench.py` 增 `accounts_detail()`（启停/凭证/登录态聚合）
      + toggle 端点 + 测试
- [ ] T3 复盘端点：`GET /api/postmortems/{platform}` 与 `/{title}`（复用
      postmortem 模块）+ 测试
- [ ] T4 运维触发：`POST /api/ops/trigger`（标记文件）+ 网关消费 + 测试
- [ ] T5 `GET /api/tools`（tool_catalog）+ 测试

## 2. 前端

- [ ] T6 AccountsPage（账号卡片：启停切换/凭证/登录态状态）
- [ ] T7 BreakdownPage（复盘列表+单篇详情，marked+dompurify 渲染）
- [ ] T8 SkillPage（运维触发三按钮+agent 工具清单）
- [ ] T9 SettingsPage（webhook 配置表单）

## 3. 验证

- [ ] T10 make check 全绿 + pnpm build
- [ ] T11 端点冒烟 + spec 场景核对

```

## openspec/changes/web-pages-batch/.openspec.yaml

- Source: openspec/changes/web-pages-batch/.openspec.yaml
- Lines: 1-2
- SHA256: e61703315c59969805e021ec521ca189369aaf8ea902d52c5e39c7fbc603598f

```md
schema: spec-driven
created: 2026-10-10

```

## openspec/changes/web-pages-batch/specs/web-workbench/spec.md

- Source: openspec/changes/web-pages-batch/specs/web-workbench/spec.md
- Lines: 1-44
- SHA256: 02dfae60de3db40d159036a7cbf500b0a08c60b840cf6d7c009610e930e68ab6

```md
# web-workbench 能力增量（web-pages-batch）

## ADDED Requirements

### Requirement: 账号管理页

账号管理页展示每个画像账号：启停状态（可切换）、加密凭证是否存在、登录态
文件是否存在；启停切换调用 governance.platform_state 并即时生效（停用后
发布路由拒绝）。

#### Scenario: 停用账号阻断发布
- **When** 账号被切换为停用
- **Then** real_platform_router 对该账号发布抛「已停用」错误

#### Scenario: 非法账号名切换被拒绝
- **When** toggle 请求的 account 不匹配 `^[A-Za-z0-9_-]+$`
- **Then** 返回 400

### Requirement: 单篇复盘页

复盘页列出指定平台的发布事件与排名；单篇详情展示 read 序列/生命周期/同期
对照证据（数据来自 postmortem 模块，只读）。

#### Scenario: 无发布事件的账号
- **When** 账号无发布事件
- **Then** 复盘列表为空态而非报错

### Requirement: 设置页

设置页查看与修改通知 webhook URL；保存后写入运行时设置文件并即时生效
（下一次 notify 使用新 URL）；非法 URL 被拒绝。

#### Scenario: 保存合法 webhook
- **When** PUT 设置提交 `https://open.feishu.cn/open-apis/bot/v2/hook/xxx`
- **Then** 返回 ok，后续 notify 投递到该 URL（mock 验证）

### Requirement: 运维操作页

运维操作页展示 agent 工具清单，并提供三个触发按钮：托管循环/数据取数/
校准——以触发标记文件落地，由常驻网关在下一调度循环消费执行。

#### Scenario: 触发标记被网关消费
- **When** POST 触发托管循环写入标记
- **Then** 网关下一循环执行 hosted_daily 并清除标记

```
