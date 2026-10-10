---
change: web-easel-alignment
design-doc: openspec/changes/web-easel-alignment/design.md
base-ref: 9b9639b
archived-with: 2026-10-10-web-easel-alignment
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

## 执行序（每项绑定 comet-task-ref）

<!-- comet-task-ref:1c4c4452-c880-4fb5-a811-5590ca6dc202 -->
- T1 `styles/index.css` 设计系统移植

<!-- comet-task-ref:0e12b587-c2af-4fd2-9e59-5d78407a73d4 -->
- T2 `index.html` 防闪脚本与字体

<!-- comet-task-ref:9f96bf38-e885-4ed1-a25a-b74164ca968b -->
- T3 卸载 react-router-dom

<!-- comet-task-ref:ecef2fcb-0e63-40b7-b051-3f0d0ed193e3 -->
- T4 页面结构迁移 components/

<!-- comet-task-ref:3c458548-c50e-44df-817c-21b9e92d02c1 -->
- T5 lib/api.ts 重写

<!-- comet-task-ref:c7eb057e-1c56-4bc1-a9ed-cdd3ed14b826 -->
- T6 八页面 Easel 范式重写

<!-- comet-task-ref:a93c1abb-4922-4b5b-aa07-87b07a679839 -->
- T7 侧边栏渐变激活条+状态点

<!-- comet-task-ref:c715ea5a-8968-4457-bdf0-ab5b528fcbd7 -->
- T8 pnpm build + grep 验收

<!-- comet-task-ref:7cd2347b-6026-4bb0-802c-f46d72b40554 -->
- T9 端点冒烟

<!-- comet-task-ref:3159a9a7-ebcc-40f1-8927-a426831ad901 -->
- T10 spec 场景核对
