---
comet_change: autonomous-observability
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-18-autonomous-observability
status: final
---

# 设计：autonomous-observability

## 高层方案

```
后端（②③ 已有 + 本变更补一条）
  GET /api/flows/runs?flow_id=   执行记录含步骤明细（store.list_runs）
  GET /api/autonomous/status     熔断态 + 预算（③）
  GET /api/feedback              校准信号（②）

前端 AutonomousPage.tsx（沿用 AutomationsPage 范式）
  ① 流程列表（名称/步骤徽标/调度/启用态 + 停用/删除/立即执行）
  ② 新建面板（名称 + 五层步骤勾选 + 调度 + 主题/平台/仅草稿）
  ③ 执行记录（每次执行：状态、耗时、逐步明细）
  ④ 状态卡：待确认 blocked / 熔断提示 / 当日预算用量
侧栏导航新增「自主运营」；E2E S13；demo 第 6 段；README 章节
```

## 关键决策

### D1：样式严格克隆 AutomationsPage（教训驱动）
此前新增页面曾自造类名（.page/.form-row/.page-empty/裸 btn-primary）导致整页裸 HTML，
用户两次目检发现。本页**逐段对齐** AutomationsPage：
`.page-scroll` + `.page-head` + `h1.page-title` + `p.page-subtitle` + `.panel/.panel-title`
+ `.field-label/.field` + `.btn .btn-sm(.btn-primary/.btn-danger)` + `.badge` + `.card`
+ `.foot-note` + `.toast.ok/.toast-icon`。自定义 CSS 只用设计 token 且最少化。

### D2：执行记录查询走既有 store，不加新表
`flow_runs` + `flow_steps` 在 ① 已建；本变更只加读侧 `list_runs()`，JOIN 两步返回树形。

### D3：看板不做「立即执行真实链路」的默认按钮风险
立即执行会真实消耗 token。E2E/demo 用 mock；页面上按钮保留（用户显式点击才跑），
但 demo 脚本不点它（避免录制时烧钱）。

### D4：blocked 与熔断在页面显著位置
这两项是「无人值守」最需要人介入的信号，放在页面顶部状态卡而不是埋在列表里。

## 风险与对策

- **风险**：样式再次跑偏 → 构建后截图目检（表单态/列表态）并与既有页对比，写进验证报告
- **风险**：执行记录 JOIN 性能 → 限制返回条数（默认 20）与步骤截断
- **风险**：预算无单价（None）→ 页面如实显示「未折算」，不显示 0

## Open Questions

无。
