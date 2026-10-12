## Purpose

定义"复制 Easel 前端源码建立本项目 Web 工程并跑起来"的验收标准：源码完整、依赖就绪、dev server 可访问。

## ADDED Requirements

### Requirement: 前端源码复制完整且保真

#### Scenario: 文件比对

- **WHEN** 对比 `apps/web/src` 与 Easel `web/frontend/src` 的同名文件
- **THEN** 内容逐行一致，目录无遗漏（`components/`、`lib/`、`styles/` 及入口文件）

#### Scenario: 静态资源就位

- **WHEN** 前端加载侧栏 logo 与对话页品牌资源
- **THEN** 资源从 `apps/web/public/static/` 加载成功，无 404

### Requirement: 前端可运行

#### Scenario: 本地启动

- **WHEN** 在 `apps/web` 安装依赖并启动 dev server
- **THEN** 服务正常监听，浏览器打开首页可渲染侧栏与工作台，控制台无致命报错

### Requirement: 后端缺失时呈现空态而非崩溃

#### Scenario: 接口未就绪

- **WHEN** 后端服务尚未就绪，前端调用接口失败
- **THEN** 页面按 Easel 既有空态/错误文案呈现，前端不崩溃、不改写源码适配
