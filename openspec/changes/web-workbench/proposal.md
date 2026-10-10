# 提案：Web 运营工作台（web-workbench）

## Why

Web 前端目前是单文件 `App.tsx`（审批/看板/日历挤在一个页面，无路由无导航），
对照参考项目 Easel 的 `web/frontend`（React 多页工作台：Dashboard/Chat/Accounts/
Profile/Outputs/Publish/Calendar/Ideas/Trends/Skill 十页）差距明显——托管形态的
「人在环」入口需要结构化页面承载，散装区块无法支撑多账号日常运营。

## What Changes

- **前端（apps/web）**：引入 react-router-dom 多页路由 + 侧边栏布局（对标 Easel），
  拆分并新增 7 个页面：概览 Dashboard / 审批中心 Approvals（含问题卡片）/
  选题看板 Ideas / 内容日历 Calendar / 画像管理 Profile / 趋势 Trends /
  内容库 Outputs；统一 `api/` 客户端模块
- **后端（apps/api）**：新增 4 组只读+受控写端点：
  - `GET /api/dashboard`（待审批数/账号启停/今日发布/最近日志）
  - `GET /api/profiles`、`GET/PUT /api/profiles/{account}`（画像查看与编辑，
    PUT 经 validate_profile fail-closed 校验）
  - `GET /api/trends/{account}`（复用校准证据引擎的基线归一化指标）
  - `GET /api/outputs/{account}`（内容库：已发布草稿产物清单）
- 现有审批/提问/看板/日历端点与行为不变（前端重组消费）

## Capabilities

- **New Capabilities**: `web-workbench`（工作台页面结构与数据端点行为）
- **Modified Capabilities**: 无（既有端点契约不变，仅新增）

## Non-Goals

- 不做 Agent 聊天页（Easel ChatPage 对标需要新的会话端点与流式协议，
  独立变更；托管审批已覆盖现有人机交互）
- 不做多平台发布中心 UI（Easel PublishPage 对标——发布走 agent+审批闭环，
  人工手发入口待 PRD 扩展）
- 不做账号登录 UI（平台登录走既有扫码/凭证链路）
- 不改发布/校准/网关等后端行为

## 关键决策

- 路由用 react-router-dom（Easel 同款形态）；构建验证纳入 `pnpm build`（tsc 严格）
- 画像编辑是**受控写**：只写 `profiles/<account>/profile.yaml`（git 追踪，可 diff 可回滚）
- 趋势数据 100% 复用 `operations.calibration.build_evidence`（不重写统计逻辑）
