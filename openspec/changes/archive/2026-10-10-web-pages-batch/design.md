---
comet_change: web-pages-batch
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-10-web-pages-batch
status: final
---

# 设计：web-pages-batch

## Context

web-workbench 已交付 8 页；本批补 Easel 页面清单中的 Accounts/Breakdown/
Skill（运维）/Settings 四页。后端已有可复用资产：governance.platform_state
（启停）、operations.postmortem（复盘证据）、core.notify（webhook）、
operations.workbench（账号列表）。缺口是：凭证/登录态存在性探针、复盘端点化、
设置持久化、运维触发机制、前端四页。

## Goals / Non-Goals

- Goals：四页 + 端点 + 测试；运维触发经标记文件由网关消费
- Non-Goals：ChatPage/PublishPage（独立变更 web-chat-publish）；Onboarding；平台登录 UI

## 决策记录

- **D1 账号管理数据面**：`operations/workbench.py` 增 `accounts_detail()`——
  聚合 profiles 账号 × platform_state 启停 × `data/credentials/<a>.sealed`
  存在性 × `data/login/xhs_state.json` 存在性。toggle 端点调
  `platform_state.set_enabled`（复用既有 fail-closed 语义），account 白名单校验同 D3。
- **D2 复盘端点化**：直接调 `operations.postmortem` 的 `top_formula`/
  `note_evidence`（不重写）；渲染交给前端（返回结构化 JSON 而非 md 文本）。
- **D3 设置持久化**：`core/settings.py`——`data/state/settings.json`
  （{notify_webhook_url}），get/set 带容错；notify.py 改为每次发送时读设置
  （env 优先级高于设置文件，保持向后兼容）。
- **D4 运维触发标记文件**：`data/state/ops-trigger.json`（键为网关任务名
  hosted_content/ops_data/health_check）；SkillPage POST 写标记（读-合并-写），
  网关 lifespan 启动 30s 间隔消费循环（原子 rename 接管防竞态，评审 W1）。
  API 与网关可能不同进程——标记文件是唯一安全通道。
- **D5 agent 工具清单**：`runtime/tools.py` 导出 `tool_catalog()`——从
  build_default_tools 的工具名+description 生成（不含闭包执行），只读展示。
- **D6 前端 markdown**：BreakdownPage 渲染复盘文本引入 marked+dompurify
  （Easel 同款两依赖）。
