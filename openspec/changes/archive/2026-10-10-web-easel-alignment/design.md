---
comet_change: web-easel-alignment
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-10-web-easel-alignment
status: final
---

# 设计：web-easel-alignment

## Context

web-workbench 的页面被用户打回：与 Easel「完全不一样」。深调
E:/Projects/Easel/web/frontend 实源（package.json/App.tsx 766-793/IdeasPage 全文/
styles/index.css :root 与布局类）确认差异根源：Easel 是零框架极简（无路由库/
无 UI 库/无 CSS 框架），设计系统 = CSS 变量令牌 + 全局原子类 + 内联 SVG 图标；
而 web-workbench 自引 react-router-dom + 自造样式体系。

## Goals / Non-Goals

- Goals：视觉与交互形态与 Easel 一致（用户肉眼可辨）；依赖保持极简
- Non-Goals：不改后端；不新增页面；不做聊天页

## 决策记录

- **D1 依赖回收**：卸载 react-router-dom（该决策已在上一变更被证明与 Easel
  形态冲突）；无路由库页面切换 = `useState<Page>` + switch，刷新保持用
  sessionStorage（Easel 无此需求，为体验增强）。
- **D2 设计系统整段移植**：从 Easel index.css 原样搬 `:root` 令牌块 +
  通用原子类（btn/chip/field/card/badge/overlay/modal/toast/page-head/
  dash-empty/kanban-*），标注来源注释；theme.css 暗色整套；index.html
  防闪脚本（localStorage 'zimeiti_theme'）。zimeiti 特有类（问题卡片等）
  按同一令牌体系补写。
- **D3 结构对齐**：页面组件移入 `src/components/`（扁平 XxxPage.tsx，Easel
  惯例，放弃 pages/ 子目录）；图标 `components/icons.tsx` 内联 SVG；
  api.ts 移 `src/lib/api.ts` 并改为 `request<T>` + `{detail}` 错误解析
  （Easel api.ts:1-25 同款）。
- **D4 路由形态**：App.tsx 顶层 `useState<Page>` + `renderPage()` switch；
  刷新保持：sessionStorage('zimeiti_page')。
- **D5 网关状态点**：侧边栏底部 status-dot 展示 /api/dashboard 账号启停
  （Easel Sidebar 同位置模式，数据源换本项目）。

## 风险

- 全局 CSS 令牌替换可能波及既有页面类名 → 页面重写时统一用新类名，旧
  App.css 自造样式整段删除（不留双轨）
