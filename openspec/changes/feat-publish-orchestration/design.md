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
