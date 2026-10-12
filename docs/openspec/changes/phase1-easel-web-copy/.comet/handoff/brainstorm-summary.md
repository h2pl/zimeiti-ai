# Brainstorm Summary

- Change: phase1-easel-web-copy
- Date: 2026-10-13

## Confirmed Technical Approach

分类：architectural（全新项目，仓库内无既有流程可改），但范围很窄——纯复制 + 跑起来，不含逻辑改写。

目录映射：

- Easel `web/frontend/src/*`（App.tsx、main.tsx、components/、lib/、styles/）→ `apps/web/src/*`
- Easel `web/frontend/package.json`、`vite.config.ts`、`tsconfig*`、`index.html` → `apps/web/`
- Easel `web/static/*` → `apps/web/public/static/`

执行顺序：复制源码与配置 → 复制静态资源 → `npm install` → 启动 dev server（端口 5173）→ 浏览器验证首页渲染。

## Key Tradeoffs and Risks

- 不改复制来的代码：后端缺失导致接口报错时，仍保持 Easel 原样（空态/错误文案由 Easel 自带逻辑呈现），这是后续能与 Easel diff 同步的前提
- 静态资源走 `public/static/`：Easel 前端以相对路径 `./static/...` 引用，放置于此可直接命中，无需改引用
- 依赖安装受网络影响 → 对齐 Easel 版本，失败即记录
- 端口冲突 → 指定 5173（Easel dev server 当前占 5174）

## Test Strategy

本变更无逻辑改动，不写单测。验收靠三步实证：

1. `apps/web/src` 与 Easel 同名文件逐文件 diff 一致
2. dev server 正常监听，启动无致命报错
3. Playwright 打开首页，确认侧栏与工作台渲染、控制台无致命错误

## Spec Patch

None（delta spec 的验收场景已覆盖）
