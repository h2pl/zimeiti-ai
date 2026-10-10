# 任务：web-workbench

## 1. 后端端点

- [ ] T1 `GET /api/dashboard`：待审批数/账号启停/今日发布数/最近日志 + 测试 <!-- comet-task:2c863dd4-8ade-4b32-9cde-fb16c551be4b -->
- [ ] T2 `GET /api/profiles` + `GET/PUT /api/profiles/{account}`（validate_profile <!-- comet-task:b071bdf4-d6a6-4508-ad3b-24ffe3ca27d3 -->
      fail-closed + account 白名单防路径遍历）+ 测试
- [ ] T3 `GET /api/trends/{account}`（复用 build_evidence）+ `GET <!-- comet-task:b5c8c120-e540-4058-b761-d10e7f69a9fc -->
      /api/outputs/{account}`（只读元数据扫描）+ 测试

## 2. 前端路由化

- [ ] T4 引入 react-router-dom；App.tsx 改 Layout（侧边栏导航）+ Routes <!-- comet-task:53af429a-26e0-4f1c-9d5b-29da24593523 -->
- [ ] T5 `src/api.ts` 类型化客户端；Approvals/Ideas/Calendar 页面从现 App.tsx 拆出 <!-- comet-task:43dfdadf-293c-4115-b5db-af1732079320 -->
- [ ] T6 Dashboard / Profile / Trends / Outputs 四个新页面（消费新端点） <!-- comet-task:934929e1-2771-4c34-a5e5-772a395255aa -->
- [ ] T7 `pnpm build` 通过（tsc 严格） <!-- comet-task:703e5394-d82c-48ba-abee-1533340ddd86 -->

## 3. 验证与收尾

- [ ] T8 make check 全绿（后端新增测试计入） <!-- comet-task:ec03c37e-90a6-4274-ab4a-df63a2b77b80 -->
- [ ] T9 入口冒烟：vite dev 起服 + 关键 API 返回 200；pnpm build 证据 <!-- comet-task:4930c6a5-f6ad-4112-858e-8d06569e8b88 -->
- [ ] T10 spec 场景核对（5 需求 6 场景逐条对照实现与测试） <!-- comet-task:76f47c71-d8d2-4edd-884a-fb0d8273a4cc -->
