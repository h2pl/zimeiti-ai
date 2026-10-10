---
comet_change: web-workbench
role: technical-design
canonical_spec: openspec
---

# 设计：web-workbench

## Context

apps/web 现状：单 `App.tsx`（审批+看板+日历+日志四区块，5s 轮询）、vite 代理
`/api → :8000`、pnpm 构建。后端已有端点：approvals/questions/kanban/calendar/
publish-log；缺 dashboard/profiles/trends/outputs。参考 Easel `web/frontend/src/`
（App.tsx 路由 + components/ 页面组件）与本项目「顶层组装器」惯例。

## Goals / Non-Goals

- Goals：路由化多页工作台、后端数据端点齐备、行为有规格有测试
- Non-Goals：聊天页、发布中心 UI、账号登录 UI（见 proposal Non-Goals）

## 决策记录

- **D1 路由选型 react-router-dom**：Easel 同款生态；新增依赖仅此一个。
  `App.tsx` 变为 Layout+Routes 组装器，页面组件拆 `src/pages/`。
- **D2 API 客户端集中**：`src/api.ts` 统一 fetch 封装（类型化返回），页面不直接
  fetch——轮询/错误处理单点维护。
- **D3 画像编辑 fail-closed**：PUT 端点服务端 `validate_profile` 校验通过才写
  `profiles/<account>/profile.yaml`；写入即 git 追踪文件变更（自用期可 diff 回滚，
  不做草稿/撤销 UI）。目录遍历防护：account 参数白名单校验（`^[A-Za-z0-9_-]+$`）。
- **D4 趋势复用证据引擎**：`GET /api/trends/{account}` 直接调
  `operations.calibration.build_evidence` 返回 baseline 字段，不新写统计。
- **D5 内容库只读扫描**：`GET /api/outputs/{account}` 扫
  `OUTPUTS_DIR/<account>/*/drafts.json` 的元数据（slug/标题/合规/created_at），
  account 参数同样白名单校验，不读正文（防路径注入与超大响应）。
- **D6 构建验证**：`pnpm build`（tsc -b + vite build）纳入变更验证证据；
  make check 维持 api 侧不变。

## 风险

- 画像 PUT 是全仓唯一受控写端点：路径白名单 + validate 双保险（D3）
- tsc 严格模式下现有 App.tsx 代码需过类型检查（已验证 `npx tsc --noEmit` 通过）
