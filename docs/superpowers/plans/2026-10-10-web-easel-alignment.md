---
change: web-easel-alignment
design-doc: openspec/changes/web-easel-alignment/design.md
base-ref: 9b9639b
---

<!-- comet-task-authority: openspec/changes/web-easel-alignment/tasks.md -->

# 实施计划：web-easel-alignment（前端对齐 Easel 设计系统）

深调结论（E:/Projects/Easel/web/frontend 实读）：Easel 前端 = 零框架极简——
无路由库（useState<Page>+switch）、无 UI 库、无 CSS 框架；设计系统 =
styles/index.css `:root` 令牌 + 全局原子类 + 内联 SVG 图标 + 暗色 theme.css。

## 改造项

1. 依赖回收：卸载 react-router-dom（唯一多余依赖）
2. 设计系统移植：`:root` 令牌块 / theme.css 暗色 / index.html 防闪脚本 /
   布局类（app-layout/sidebar 264px 渐变激活条/main-content 暖纸光晕/page-head/
   btn/chip/field/card/badge/overlay/modal/toast/dash-empty）
3. 结构对齐：src/components/XxxPage.tsx 扁平页面 + components/icons.tsx +
   lib/api.ts（request<T> + {detail} 错误解析）
4. 路由形态：App.tsx `useState<Page>` + switch（删 react-router）
5. 页面重写（8 页，Easel 类名与模式）：Dashboard/Approvals/Ideas/Calendar/
   Profile/Trends/Outputs/Logs

## 验证

- `pnpm build`（tsc 严格）+ 无 react-router 残留 grep + 端点冒烟
- 后端不动（端点契约已就绪）

回滚：分支单 commit revert。
