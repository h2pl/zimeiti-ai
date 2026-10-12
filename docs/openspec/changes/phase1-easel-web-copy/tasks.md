## 1. 复制前端源码与配置

- [x] 1.1 复制 Easel `web/frontend/src`（App.tsx、main.tsx、components/、lib/、styles/）→ `apps/web/src` <!-- comet-task:919bda01-1af7-4eca-aac2-60dc7d1aafe7 -->
- [x] 1.2 复制工程配置（package.json、vite.config.ts、tsconfig*、index.html）→ `apps/web` <!-- comet-task:477481cb-03ab-4722-85b7-543201763487 -->
- [x] 1.3 验证：`apps/web/src` 与 Easel 同名文件逐行一致，目录无遗漏 <!-- comet-task:8be50b5c-497b-4ce7-b0b2-ce22f2f6e968 -->

## 2. 复制静态资源

- [x] 2.1 复制 `Easel/web/static/*` → `apps/web/public/static/` <!-- comet-task:87877329-e19c-4ae1-8ccf-144693c8ba30 -->
- [x] 2.2 验证：资源文件齐全，引用路径为 `./static/...` <!-- comet-task:b60b56cd-38ec-463d-80e0-644133b315ac -->
- [x] 2.3 清理评审发现的未引用 Easel artifact 页面与大体积媒体（index.html/main.html/onepage.html/showcase/easel-icon.png/marked.umd.js），保留源码引用的资源 <!-- comet-task:48905f7d-0f94-4640-b1e5-1bda729c89e5 -->

## 3. 安装依赖并跑起来

- [x] 3.1 在 `apps/web` 执行依赖安装 <!-- comet-task:ad1fd4f8-95c3-400c-821c-dd9b72da96a7 -->
- [x] 3.2 启动 dev server（指定端口避免冲突） <!-- comet-task:00483cb7-7959-4875-b1f0-e3634f32efee -->
- [x] 3.3 浏览器打开首页，确认侧栏与工作台渲染、控制台无致命报错 <!-- comet-task:634a963d-870b-4aa8-88a2-ff5a82152db3 -->
