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
