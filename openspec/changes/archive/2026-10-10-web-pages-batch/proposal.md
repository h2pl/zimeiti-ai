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
