# Comet Design Handoff

- Change: phase1-easel-web-copy
- Phase: design
- Mode: compact
- Context hash: 439b097cd3290205eb48c48bc2e36d3540ee244d84014af96e05d2c82a9bf8db

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/phase1-easel-web-copy/proposal.md

- Source: docs/openspec/changes/phase1-easel-web-copy/proposal.md
- Lines: 1-28
- SHA256: a0bd5299d1ac761e2196891d1517a7437420588b9019c33aad1fd005240fbcde

```md
## Why

这是全新项目（起点分支 `zimeiti-init` 只有需求文档，无代码）。按 `docs/prd/zimeiti-ai-prd.md`：产品能力目标为 **Easel ∪ xiaobei**，阶段一是先复制实现 Easel。

本变更是阶段一的前半部：**把 Easel 前端复制过来并跑起来**。后端复制由独立变更 `phase1-easel-api-copy` 承担。

## What Changes

- 新建 `apps/web`：整份复制 Easel 前端源码 `web/frontend/src`（`App.tsx`、`main.tsx`、`components/`、`lib/`、`styles/`）
- 复制工程配置：`package.json`、`vite.config.ts`、`tsconfig*`、`index.html`
- 复制静态资源：`Easel/web/static/*` → `apps/web/public/static/`
- 安装依赖并启动 dev server，确认页面可访问

## Capabilities

### New Capabilities

- `easel-web-copy`: 以 Easel 前端源码为起点的 Web 工程——源码复制完整、依赖就绪、本地可运行

### Modified Capabilities

（无。全新项目，无既有能力规格。）

## Impact

- 新增 `apps/web/`（源码、配置、静态资源、依赖清单）
- 本地前端启动方式改为 `apps/web` 下的 dev server
- 本变更只复制并跑起来，不改写复制来的前端代码；后端接口未就绪时按 Easel 既有空态呈现

```

## docs/openspec/changes/phase1-easel-web-copy/design.md

- Source: docs/openspec/changes/phase1-easel-web-copy/design.md
- Lines: 1-71
- SHA256: c02df74b1e144db018f22e4c052e0ce820f39362fc04369a82a932d1b3077c2b

```md
---
comet_change: phase1-easel-web-copy
role: technical-design
canonical_spec: openspec
---

## Context

全新项目，起点分支 `zimeiti-init` 无代码。本变更复制 Easel 前端，后端复制由 `phase1-easel-api-copy` 承担。

复制源：`E:\Projects\Easel\web\frontend`（`src/`、`package.json`、`vite.config.ts`、`tsconfig*`、`index.html`）与 `E:\Projects\Easel\web\static`。

## Goals / Non-Goals

**Goals:**

- 复制 Easel 前端源码与配置到 `apps/web`
- 装依赖、启动 dev server、页面可访问

**Non-Goals:**

- 不复制/改造后端
- 不改写复制来的前端代码
- 不做 OpenClaw 解耦（归后端变更）

## Decisions

### 决策 1：整份复制，先跑起来再改

- **选择**：`apps/web/src` 整份复制自 Easel，本变更只求跑通
- **理由**：先拿到与 Easel 一致的基线，后续任何调整都有明确对照
- **备选**：边复制边改写 → 差异不可控，出问题难定位，否决

### 决策 2：配置随源码一起复制

- **选择**：`package.json`、`vite.config.ts`、`tsconfig*`、`index.html` 一并复制并对齐
- **理由**：Easel 代码假设其构建配置（如 `base: './'` 适配代理），自造配置易引入不必要差异
- **备选**：自行新建配置 → 无旧配置可依，且与源码假设冲突，否决

### 决策 3：静态资源放 `public/static/`

- **选择**：`Easel/web/static/*` → `apps/web/public/static/`
- **理由**：Easel 前端以相对路径 `./static/...` 引用资源，放在 `public/static/` 可直接命中
- **备选**：改引用路径 → 需改源码，违背"不改复制来的代码"，否决

## Risks / Trade-offs

- **[风险] 后端未就绪导致接口报错** → 缓解：本变更只验收页面可渲染、无致命报错
- **[风险] 依赖安装受网络/平台影响** → 缓解：对齐 Easel 版本，安装失败即记录
- **[风险] 端口冲突** → 缓解：dev server 端口可指定，避免与既有服务冲突

## Test Strategy

本变更无逻辑改动，不写单测。验收靠三步实证：

1. `apps/web/src` 与 Easel 同名文件逐文件 diff 一致
2. dev server 正常监听，启动无致命报错
3. Playwright 打开首页，确认侧栏与工作台渲染、控制台无致命错误

## Migration Plan

1. 复制 `web/frontend/src` 与工程配置 → `apps/web`
2. 复制 `web/static/*` → `apps/web/public/static/`
3. 安装依赖
4. 启动 dev server（端口 5173），浏览器验证首页渲染

**回滚**：分支隔离，丢弃分支即回到 `zimeiti-init`。

## Open Questions

- 无（本变更只做复制与跑通）

```

## docs/openspec/changes/phase1-easel-web-copy/tasks.md

- Source: docs/openspec/changes/phase1-easel-web-copy/tasks.md
- Lines: 1-16
- SHA256: 05d891a05daf3e49d7ec253ca957b0d86dea5fb032e7362e2932798fb7dc74ff

```md
## 1. 复制前端源码与配置

- [ ] 1.1 复制 Easel `web/frontend/src`（App.tsx、main.tsx、components/、lib/、styles/）→ `apps/web/src`
- [ ] 1.2 复制工程配置（package.json、vite.config.ts、tsconfig*、index.html）→ `apps/web`
- [ ] 1.3 验证：`apps/web/src` 与 Easel 同名文件逐行一致，目录无遗漏

## 2. 复制静态资源

- [ ] 2.1 复制 `Easel/web/static/*` → `apps/web/public/static/`
- [ ] 2.2 验证：资源文件齐全，引用路径为 `./static/...`

## 3. 安装依赖并跑起来

- [ ] 3.1 在 `apps/web` 执行依赖安装
- [ ] 3.2 启动 dev server（指定端口避免冲突）
- [ ] 3.3 浏览器打开首页，确认侧栏与工作台渲染、控制台无致命报错

```

## docs/openspec/changes/phase1-easel-web-copy/.openspec.yaml

- Source: docs/openspec/changes/phase1-easel-web-copy/.openspec.yaml
- Lines: 1-2
- SHA256: 010447270992e8e9533b7bbfb4dbdecda78eab560f05c50428c80463aa9e0ec1

```md
schema: spec-driven
created: 2026-10-13

```

## docs/openspec/changes/phase1-easel-web-copy/specs/easel-web-copy/spec.md

- Source: docs/openspec/changes/phase1-easel-web-copy/specs/easel-web-copy/spec.md
- Lines: 1-31
- SHA256: 51900ed93ab544496617ff9dfd0ad901f8457b784498c7d3a121fcb2825b4a75

```md
## Purpose

定义"复制 Easel 前端源码建立本项目 Web 工程并跑起来"的验收标准：源码完整、依赖就绪、dev server 可访问。

## ADDED Requirements

### Requirement: 前端源码复制完整且保真

#### Scenario: 文件比对

- **WHEN** 对比 `apps/web/src` 与 Easel `web/frontend/src` 的同名文件
- **THEN** 内容逐行一致，目录无遗漏（`components/`、`lib/`、`styles/` 及入口文件）

#### Scenario: 静态资源就位

- **WHEN** 前端加载侧栏 logo 与对话页品牌资源
- **THEN** 资源从 `apps/web/public/static/` 加载成功，无 404

### Requirement: 前端可运行

#### Scenario: 本地启动

- **WHEN** 在 `apps/web` 安装依赖并启动 dev server
- **THEN** 服务正常监听，浏览器打开首页可渲染侧栏与工作台，控制台无致命报错

### Requirement: 后端缺失时呈现空态而非崩溃

#### Scenario: 接口未就绪

- **WHEN** 后端服务尚未就绪，前端调用接口失败
- **THEN** 页面按 Easel 既有空态/错误文案呈现，前端不崩溃、不改写源码适配

```
