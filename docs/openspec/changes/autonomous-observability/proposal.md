---
comet_change: autonomous-observability
---

# autonomous-observability：自主运营看板与可观测性

## Why

自主运行批次 ④/④：前三个变更让链路能编排（①）、能回流（②）、敢无人值守（③），
但**运行状态只在后端**：流程有哪些、最近跑得怎样、有没有待人工确认的 blocked、
预算花到哪、熔断是否跳闸——用户看不到。没有可见性就不叫「托管给 agent」，
用户不会放心让它自己跑。

xiaobei 的做法是通过 IM 随时问、每日复盘推送；本批次不引入 IM（用户明确先不做），
改为**页面看板 + 状态端点**。

## What Changes

- 后端：`GET /api/flows/runs`（流程执行记录含逐步明细）+ 既有 `/api/autonomous/status`
  （熔断态/预算/blocked）与 `/api/feedback`（校准信号）已在 ②③ 交付
- 前端新增「自主运营」页（`AutonomousPage.tsx`，沿用 AutomationsPage 的设计体系）：
  流程列表（名称/步骤/调度/启用态）、新建（勾选五层步骤）、最近执行记录（逐步状态）、
  **待确认 blocked 清单**、熔断提示、当日预算用量
- 侧栏导航新增「自主运营」项
- E2E 新增 S13 场景（覆盖该页）；demo 新增第 6 段
- README 补「自主运营」章节

## Non-Goals

- **不做 IM 通道**（用户明确先不做）：看板与 API 即可见
- 不做告警推送（邮件/IM）：blocked 与熔断在页面可见，推送后续再议
- 不改护栏语义（②③ 已定）

## Capabilities

### New Capabilities

- `autonomous-observability`：自主运营状态在页面可见——流程、执行记录、待人工确认
  项、熔断态、预算用量一处可查

## Impact

`zimeiti_autonomous` 新增执行记录查询；前端新增一个页面与导航项；E2E 场景 12→13；
demo 5→6 段；README 增章。既有页面与任务行为零变化。
