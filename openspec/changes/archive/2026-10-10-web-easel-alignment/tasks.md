# 任务：web-easel-alignment

## 1. 设计系统移植

- [x] T1 `styles/index.css`：Easel `:root` 令牌 + 通用原子类整段移植（标注来源）， <!-- comet-task:1c4c4452-c880-4fb5-a811-5590ca6dc202 -->
      删除自造 App.css 样式；`styles/theme.css` 暗色主题
- [x] T2 `index.html`：防闪烁主题脚本 + 非阻塞字体加载 <!-- comet-task:0e12b587-c2af-4fd2-9e59-5d78407a73d4 -->

## 2. 结构对齐

- [x] T3 卸载 react-router-dom；App.tsx `useState<Page>` + switch + 刷新保持 <!-- comet-task:9f96bf38-e885-4ed1-a25a-b74164ca968b -->
- [x] T4 页面移 `src/components/XxxPage.tsx` 扁平结构；`components/icons.tsx` <!-- comet-task:ecef2fcb-0e63-40b7-b051-3f0d0ed193e3 -->
- [x] T5 `lib/api.ts` 重写：`request<T>` + `{detail}` 错误解析 + 类型集中 <!-- comet-task:3c458548-c50e-44df-817c-21b9e92d02c1 -->

## 3. 页面重写（Easel 范式）

- [x] T6 8 页面全部重写为 Easel 类名与模式（page-head/dash-empty/toast/kanban-*） <!-- comet-task:c7eb057e-1c56-4bc1-a9ed-cdd3ed14b826 -->
- [x] T7 侧边栏：渐变激活条 + 网关状态点（/api/dashboard 数据） <!-- comet-task:a93c1abb-4922-4b5b-aa07-87b07a679839 -->

## 4. 验证

- [x] T8 `pnpm build` + grep 验收（无 react-router 残留、无自造配色残留） <!-- comet-task:c715ea5a-8968-4457-bdf0-ab5b528fcbd7 -->
- [x] T9 端点冒烟（dev 起服 + 关键 API 200） <!-- comet-task:7cd2347b-6026-4bb0-802c-f46d72b40554 -->
- [x] T10 spec 场景核对（4 需求 4 场景） <!-- comet-task:3159a9a7-ebcc-40f1-8927-a426831ad901 -->
