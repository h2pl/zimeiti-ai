# web-easel-alignment Specification

## Purpose
TBD - created by archiving change web-easel-alignment. Update Purpose after archive.

## Requirements

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
