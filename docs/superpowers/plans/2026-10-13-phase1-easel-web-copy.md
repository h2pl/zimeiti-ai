---
change: phase1-easel-web-copy
design-doc: docs/openspec/changes/phase1-easel-web-copy/design.md
base-ref: db02161b0e65318f7a9be4e675a7e8e698376f7e
archived-with: 2026-10-13-phase1-easel-web-copy
---

<!-- comet-task-authority: docs/openspec/changes/phase1-easel-web-copy/tasks.md -->

# 实施计划：复制 Easel 前端并跑起来

配置：autonomous / direct / standard。范围仅为复制与启动验证，不改写复制来的代码。

## 任务 1：复制前端源码与配置

<!-- comet-task-ref:919bda01-1af7-4eca-aac2-60dc7d1aafe7 -->
复制 `E:\Projects\Easel\web\frontend\src`（含 App.tsx、main.tsx、components/、lib/、styles/）→ `apps/web/src`

<!-- comet-task-ref:477481cb-03ab-4722-85b7-543201763487 -->
复制工程配置 `package.json`、`vite.config.ts`、`tsconfig*`、`index.html` → `apps/web`

<!-- comet-task-ref:8be50b5c-497b-4ce7-b0b2-ce22f2f6e968 -->
验收：`diff -r` 比对 `apps/web/src` 与 Easel 同名文件逐行一致，目录无遗漏

## 任务 2：复制静态资源

<!-- comet-task-ref:87877329-e19c-4ae1-8ccf-144693c8ba30 -->
复制 `E:\Projects\Easel\web\static\*` → `apps/web/public/static/`

<!-- comet-task-ref:b60b56cd-38ec-463d-80e0-644133b315ac -->
验收：资源文件齐全，前端引用路径为 `./static/...`

## 任务 3：安装依赖并跑起来

<!-- comet-task-ref:ad1fd4f8-95c3-400c-821c-dd9b72da96a7 -->
在 `apps/web` 执行 `npm install`

<!-- comet-task-ref:00483cb7-7959-4875-b1f0-e3634f32efee -->
启动 dev server（端口 5173，避免与 Easel dev server 5174 冲突）

<!-- comet-task-ref:634a963d-870b-4aa8-88a2-ff5a82152db3 -->
验收：Playwright 打开首页，确认侧栏与工作台渲染、控制台无致命报错

## 风险与回滚

- 依赖安装受网络影响 → 对齐 Easel 版本，失败即记录
- 后端缺失 → 页面按 Easel 自带空态呈现，不改前端代码
- 回滚：分支隔离，丢弃分支即回到 `zimeiti-init`

<!-- comet-task-ref:48905f7d-0f94-4640-b1e5-1bda729c89e5 -->
## 任务 2.3（Verify 评审返修）：清理未引用静态资源

删除未引用的 Easel artifact 页面与大体积媒体（index.html/main.html/onepage.html/showcase/easel-icon.png/marked.umd.js），仅保留源码引用的 easel-icon-transparent.png。验收：删除后构建通过、页面渲染无 404、public/static 仅剩被引用资源。
