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
