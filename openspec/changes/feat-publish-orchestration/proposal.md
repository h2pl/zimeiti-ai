# 提案：发布编排 UI（feat-publish-orchestration）

## Why

对齐缺口矩阵 ⚠ 第 2 项：PublishCenter 只有入队+队列状态；Easel PublishPage
有完整的单篇发布编排——发布前预检结果、定时排期、队列条目管理。本变更把
PublishCenter 补成完整的发布编排 UI。

## What Changes

- 后端：
  - `GET /api/preflight/{account}/{slug}`：对草稿正文跑 preflight 约束校验，
    返回逐项结果（fail-closed 结论）
  - enqueue 支持未来时间 run_at（定时排期，run_at 必须为合法 ISO 时间）
  - `POST /api/publish-queue/{entry_id}/cancel`：pending 条目取消
    （终态不可取消；写入审计）
- 前端：PublishCenterPage 增强——
  - 入队前预检展示（逐项通过/拒绝）
  - 定时入队（datetime-local 选择）
  - 队列 pending 条目取消按钮

## Capabilities

- **Modified Capabilities**: `publish-center`（ADDED：预检/定时/取消需求）

## Non-Goals

- 不做即时发布绕过审批（发布仍走队列→网关→执行器→HITL 既有链路）
- 不做跨账号批量编排

## 关键决策

- 预检复用 governance.preflight 的既有校验函数（不重写规则）
- cancel 复用 queue.mark（pending→cancelled 非终态转换，终态保护逻辑不变）
