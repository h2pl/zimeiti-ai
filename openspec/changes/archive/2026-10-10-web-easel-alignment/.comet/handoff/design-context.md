# Comet Design Handoff

- Change: web-easel-alignment
- Phase: design
- Mode: compact
- Context hash: 9076c1c53b9808d19ab72d5bb9bd60224c3473452d1db20b376f47a51eeb1735

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/web-easel-alignment/proposal.md

- Source: openspec/changes/web-easel-alignment/proposal.md
- Lines: 1-40
- SHA256: 2e1027c814445e61bc64715d101752b1aa10227a4545314f833da8fe37c34662

```md
# 提案：前端对齐 Easel 设计系统（web-easel-alignment）

## Why

web-workbench 交付的页面被用户打回：「和 Easel 完全不一样」——只抄了页面名，
组件/样式全是自造（自引 react-router-dom、自造配色与布局），未读 Easel 前端
源码。深调（E:/Projects/Easel/web/frontend 实读）后确认 Easel 的实现路线是
零框架极简：无路由库、无 UI 库、无 CSS 框架，设计系统 = CSS 变量令牌 +
全局原子类 + 内联 SVG 图标。对齐 = 整套移植该体系，而非继续自造。

## What Changes

- **BREAKING（前端内部）**：移除 react-router-dom，路由改为 `useState<Page>`
  + switch 渲染（Easel 同款，无路由库）
- 移植 Easel 设计系统：`styles/index.css` `:root` 设计令牌 + 原子类
  （btn/chip/field/card/badge/overlay/modal/toast/page-head/dash-empty/kanban-*）、
  `theme.css` 暗色主题、`index.html` 防闪脚本与非阻塞字体加载
- 布局对齐：264px 渐变侧边栏（激活态渐变左条）+ main-content 暖纸光晕背景 +
  page-head 模式；侧边栏加网关状态点
- 页面重写为 Easel 范式：扁平 `XxxPage.tsx`、`fetchXxx().then(setState)`、
  空态 `.dash-empty`、自制 toast、COLUMNS 常量看板、图标组件 `icons.tsx`
- `lib/api.ts` 重写为 `request<T>` 泛型封装（FastAPI `{detail}` 错误解析）
- 后端零变更（端点契约已就绪）

## Capabilities

- **New Capabilities**: `web-easel-alignment`（前端视觉与交互形态规格）
- **Modified Capabilities**: 无（后端契约不变）

## Non-Goals

- 不新增页面（8 页维持）；不做聊天页/发布中心 UI
- 不改后端任何行为
- 不做暗色模式之外的主题定制

## 关键决策

- 整段移植 Easel CSS 令牌与布局类（标注来源），而非再自造——「整段复用时
  连错误处理一起照抄」铁律的前端版
- 无路由库不是偷懒：Easel 8 页同款形态，页面切换是纯状态切换

```

## openspec/changes/web-easel-alignment/design.md

- Source: openspec/changes/web-easel-alignment/design.md
- Lines: 1-44
- SHA256: bcffe49279900fa45dd3e708472e27ba2fee989a8c9b519d674b6ba2ece5ce1e

```md
---
comet_change: web-easel-alignment
role: technical-design
canonical_spec: openspec
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

```

## openspec/changes/web-easel-alignment/tasks.md

- Source: openspec/changes/web-easel-alignment/tasks.md
- Lines: 1-24
- SHA256: 52959c8777f45784f52f533bc537306304a15f86baebeec2593060c209f2dc0c

```md
# 任务：web-easel-alignment

## 1. 设计系统移植

- [ ] T1 `styles/index.css`：Easel `:root` 令牌 + 通用原子类整段移植（标注来源），
      删除自造 App.css 样式；`styles/theme.css` 暗色主题
- [ ] T2 `index.html`：防闪烁主题脚本 + 非阻塞字体加载

## 2. 结构对齐

- [ ] T3 卸载 react-router-dom；App.tsx `useState<Page>` + switch + 刷新保持
- [ ] T4 页面移 `src/components/XxxPage.tsx` 扁平结构；`components/icons.tsx`
- [ ] T5 `lib/api.ts` 重写：`request<T>` + `{detail}` 错误解析 + 类型集中

## 3. 页面重写（Easel 范式）

- [ ] T6 8 页面全部重写为 Easel 类名与模式（page-head/dash-empty/toast/kanban-*）
- [ ] T7 侧边栏：渐变激活条 + 网关状态点（/api/dashboard 数据）

## 4. 验证

- [ ] T8 `pnpm build` + grep 验收（无 react-router 残留、无自造配色残留）
- [ ] T9 端点冒烟（dev 起服 + 关键 API 200）
- [ ] T10 spec 场景核对（4 需求 4 场景）

```

## openspec/changes/web-easel-alignment/.openspec.yaml

- Source: openspec/changes/web-easel-alignment/.openspec.yaml
- Lines: 1-2
- SHA256: e61703315c59969805e021ec521ca189369aaf8ea902d52c5e39c7fbc603598f

```md
schema: spec-driven
created: 2026-10-10

```

## openspec/changes/web-easel-alignment/specs/web-easel-alignment/spec.md

- Source: openspec/changes/web-easel-alignment/specs/web-easel-alignment/spec.md
- Lines: 1-41
- SHA256: 5e3543f45f4b91c015c878751d57741303a2d471df13ea2be3dd7178fa7d04a7

```md
# web-easel-alignment 能力增量

## ADDED Requirements

### Requirement: Easel 设计系统移植

前端视觉体系与 Easel 一致：`:root` CSS 变量令牌（色板/圆角/阴影/缓动）、
暖纸光晕主区背景、渐变激活条侧边栏、暗色主题变量整套覆盖、防闪烁脚本。
前端依赖中不得存在 react-router-dom / UI 组件库 / CSS 框架。

#### Scenario: 依赖极简
- **When** 检查 apps/web/package.json dependencies
- **Then** 无 react-router-dom、无 UI 库、无 CSS 框架（Easel 同款极简）

### Requirement: 无路由库页面切换

页面切换用 `useState<Page>` + switch 渲染，不引入路由库；刷新保持当前页
（sessionStorage 持久化）。

#### Scenario: 侧边栏切换页面
- **When** 点击侧边栏导航项
- **Then** 主区渲染对应页面，激活态导航项显示渐变左条

### Requirement: 页面 Easel 范式

每个页面组件：扁平 `XxxPage.tsx` 默认导出、`page-head`（标题+副标题）、
空态 `.dash-empty`、错误降级 toast、数据经 `lib/api.ts` 的 `request<T>`
（错误取后端 `{detail}`）。

#### Scenario: 空态渲染
- **When** 看板某列无选题
- **Then** 列内渲染 `.kanban-empty` 空文案而非报错

### Requirement: 画像受控编辑保持

画像页编辑功能保持 web-workbench 的行为契约：PUT 非法输入 400 且
profile.yaml 不变；前端错误提示取后端 `{detail}`。

#### Scenario: 编辑失败提示后端原因
- **When** PUT 返回 400
- **Then** 页面 toast 显示后端 `{detail}` 文本

```
