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
