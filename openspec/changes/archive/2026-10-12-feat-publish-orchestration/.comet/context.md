# Comet Design Handoff

- Change: feat-publish-orchestration
- Phase: design
- Mode: compact
- Context hash: 8014e4fcf1d59489da68ba800ad44c93639537e78e6996b7b39fe5dcd9b7f280

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/feat-publish-orchestration/proposal.md

- Source: openspec/changes/feat-publish-orchestration/proposal.md
- Lines: 1-34
- SHA256: a56b2382656ab251c8883262b68c7d66abeb70f4ca44ca9ec1be9120f6303f86

```md
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

```

## openspec/changes/feat-publish-orchestration/design.md

- Source: openspec/changes/feat-publish-orchestration/design.md
- Lines: 1-28
- SHA256: b08273df191d75727c7273dcf8d5309d28eff2c5953da29b7a6da22350678a2e

```md
---
comet_change: feat-publish-orchestration
role: technical-design
canonical_spec: openspec
---

# 设计：feat-publish-orchestration

## Context

PublishCenter 已有入队+队列状态。Easel PublishPage 的编排要素缺三件：发布前
预检结果、定时排期、队列条目取消。后端已有可复用资产：governance.preflight
（约束校验，返回违规列表）、queue.mark（终态保护）、governance/queue 的
drafts_path 目录约定。

## 决策记录

- **D1 预检端点**：`GET /api/preflight/{account}/{slug}` → 用
  workbench.output_detail 取双平台 draft，对每平台 draft 调
  `governance.preflight(account, draft)` 返回逐项违规列表。
  返回 {preflight: {xhs: [...], gzh: [...]}, passed: bool}。
- **D2 cancelled 语义**：TERMINAL_STATUS 增 `cancelled`（取消即终态，
  终态保护逻辑不变）；cancel 端点 = mark(entry_id, "cancelled", reason)，
  条目不存在 404、已终态 409。
- **D3 定时排期**：enqueue 的 run_at 已支持任意 ISO 时间；本变更补校验
  （可解析 + 告警过去时间→400）。前端 datetime-local 选择。
- **D4 前端编排**：入队前自动跑预检并展示逐项结果（违规→禁用入队按钮，
  fail-closed）；pending 条目带取消按钮。

```

## openspec/changes/feat-publish-orchestration/tasks.md

- Source: openspec/changes/feat-publish-orchestration/tasks.md
- Lines: 1-7
- SHA256: e12d60fe03957a97184d7be906225c28b3ace70510ecaa64b4328d7be88821c8

```md
# 任务：feat-publish-orchestration

- [ ] T1 queue.py：TERMINAL_STATUS 增 cancelled + 测试
- [ ] T2 预检端点 GET /api/preflight/{account}/{slug} + 测试
- [ ] T3 enqueue run_at 校验 + cancel 端点 + 测试
- [ ] T4 PublishCenterPage：预检展示/定时入队/取消按钮
- [ ] T5 make check + pnpm build + spec 场景核对

```

## openspec/changes/feat-publish-orchestration/.openspec.yaml

- Source: openspec/changes/feat-publish-orchestration/.openspec.yaml
- Lines: 1-2
- SHA256: 1dfdca412094f24473d8b842866201ec26f200b29b17064b03f1e4982c35a7b9

```md
schema: spec-driven
created: 2026-10-12

```

## openspec/changes/feat-publish-orchestration/specs/publish-center/spec.md

- Source: openspec/changes/feat-publish-orchestration/specs/publish-center/spec.md
- Lines: 1-29
- SHA256: ee8377e90f7c8f24a19336306064b639c3a008bd114a7798420aeff003212380

```md
# publish-center 能力增量（feat-publish-orchestration）

## ADDED Requirements

### Requirement: 发布前预检

入队前可对草稿执行约束预检：逐平台返回违规列表（复用 governance.preflight），
存在违规时入队按钮禁用（fail-closed）。

#### Scenario: 违规草稿禁止入队
- **When** 草稿标题超过平台限制
- **Then** 预检返回该违规项，前端禁用入队按钮并展示违规明细

### Requirement: 定时排期

入队可指定未来运行时间（datetime-local）；过去时间或非法时间被拒绝（400）。

#### Scenario: 定时入队
- **When** 指定明天的 run_at 入队
- **Then** 队列条目 run_at 为该时间，状态 pending

### Requirement: 队列取消

pending 条目可取消（状态转 cancelled 终态）；终态条目取消返回 409；
不存在返回 404。

#### Scenario: 取消 pending 条目
- **When** 对 pending 条目发起取消
- **Then** 状态转为 cancelled，队列页徽章更新

```
