---
comet_change: autonomous-flow
---

# autonomous-flow：定时任务支持「运营流程编排」

## Why

用户诉求：让自媒体 agent **自主运行**（无人值守运营）。对齐过程中澄清的语义是
「把运营托管给 agent 自己跑」，不是部署形态上的 self-hosting。

现状盘点（grep 级）：

- **已有**：定时调度器（`automations/scheduler.py`：cron/HH:MM、租约防重、
  `automation_runs` 落记录、产出归档 `outputs/_automations/`）+ 五层运营技能
  （discover→plan→produce→publish→review）
- **缺口**：定时任务的 payload 只能是**单条 prompt** 或**单个 case 脚本**
  （`store.py` 注释即写明 `case=脚本参数 / prompt=指令文本`）——**到点无法自动
  跑完整条运营链路**。用户要「自主运行」，第一步就是让一个定时任务能编排完整流程

xiaobei 的对应能力是常驻 daemon + 定时复盘 + `published-track` 数据回流；本批次
不搬其代码（SQLite + bash + openclaw 绑定），用 zimeiti 自己的 PG + 调度 +
五层技能实现。

## What Changes

- **新建 `zimeiti_autonomous` 包**（与 `zimeiti_harness` / `zimeiti_api` 三包并列）：
  - `flows.py`：运营流程定义——五层步骤模板 + 可裁剪步骤集 + 每步配置
  - `runner.py`：串行执行 flow，逐步落 `flow_runs` / 步骤级记录，产出逐层归档
  - `store.py`：流程与执行记录持久化（PG，幂等建表）
- **调度分发**：`automations` 新增 `kind=flow`——到点把 payload 指向的流程交给
  runner 执行（复用既有租约防重与执行记录通道）
- **注入纪律**：runner 的 agent 入口由组装层注入（`set_agent_entry`），包内不
  import harness（对齐 personas/scheduler 既有范式，分层守卫可复用）
- **API**：`/api/flows` 增删改查 + 立即执行（前端看板留给后续变更，本变更只做后端）

## Non-Goals

- **不做数据回流**（发布数据 → 校准下一轮选题）：独立变更 `autonomous-feedback`
- **不做无人值守护栏**（重试/熔断/成本上限/自主模式 HITL 策略）：本变更失败即停并
  如实记录，护栏独立变更 `autonomous-guardrails`
- **不做前端看板**：本变更只交付后端能力 + 探针；UI 与告警在 `autonomous-observability`
- 不改五层技能内容本身，只做编排层

## Capabilities

### New Capabilities

- `autonomous-flow`：定时任务可编排完整运营流程（发现→选题→创作→发布→复盘可裁剪），
  每步状态与产出可追溯

## Impact

新增 `zimeiti_autonomous` 包（依赖 `zimeiti_api.core`）；`automations/store.py`
与 `scheduler.py` 扩展 `kind=flow`；新增 `/api/flows` 端点；app.py 注入 agent
入口并建表。既有 `case`/`prompt` 两类任务行为零变化。
