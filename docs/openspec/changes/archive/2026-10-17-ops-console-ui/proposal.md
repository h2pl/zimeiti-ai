---
comet_change: ops-console-ui
---

# ops-console-ui：运营控制台（定时任务 + 用量统计）

## Why

前两个批次把后端能力补齐了，但**用户看不见也配不了**：

- `/api/automations`（定时任务的增删改查、立即执行、执行记录）**无任何前端引用**
  ——想「每天早上自动出稿」只能调 API 或改环境变量
- `/api/usage`（会话 token 统计）同样无 UI——不知道哪轮对话吃了多少 token
- `ZIMEITI_FALLBACK_MODELS`（模型 fallback 链）、`ZIMEITI_SUBAGENT_MODEL`（子代理模型）
  只能改环境变量，设置面板不可配

对照 OpenClaw：它的定时/用量/模型配置都在控制台可见可改。我们后端已就位，缺的是产品面。

## What Changes

- **新增「自动化」页**（侧栏导航项）：定时任务列表（名称/类型/时刻/下次运行/开关）、
  新建（名称+类型+每日时刻+指令）、立即执行、删除、最近执行记录（状态+摘要+耗时）
- **用量概览**：工作台新增用量卡片（近 30 天 prompt/completion token 汇总），
  设置面板展示按模型/会话的明细
- **设置面**：fallback 链与子代理模型在设置面板可见（只读展示当前环境变量取值 +
  如何修改的说明）——不提供写入（避免误改运行时环境变量造成不一致）

## Non-Goals

- cron 表达式（后端只支持每日 HH:MM，UI 不超前）
- 用量金额换算（无单价数据，只展示 token）
- 定时任务的执行日志全文查看（只展示摘要，全文在 outputs/_automations/）
- 后端改动（端点已齐）

## Capabilities

### New Capabilities

- `automations-console`：定时任务在 UI 可见可管（列表/新建/开关/立即执行/删除/执行记录）
- `usage-observability`：会话用量在 UI 可查（汇总卡片 + 明细）

## Impact

前端新增 1 个页面组件 + 1 个用量卡片；侧栏新增 1 个导航项；无后端改动。
