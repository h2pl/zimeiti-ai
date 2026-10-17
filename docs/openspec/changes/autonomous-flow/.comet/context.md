# Comet Design Handoff

- Change: autonomous-flow
- Phase: design
- Mode: compact
- Context hash: 07eacefe558efea1bdf2cbf70ab87a6916cd5075402b0f2134424bbf467e393f

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/autonomous-flow/proposal.md

- Source: docs/openspec/changes/autonomous-flow/proposal.md
- Lines: 1-56
- SHA256: 7bd628268568b64242c77712b2e56ded01c56f7fc17dd7a537d21bc1b56a7f5b

```md
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

```

## docs/openspec/changes/autonomous-flow/design.md

- Source: docs/openspec/changes/autonomous-flow/design.md
- Lines: 1-61
- SHA256: 7692d0c8dd1979e2a6cf9af1a70f108ffbd69d1840360e08cba827e7257b9285

```md
---
comet_change: autonomous-flow
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：autonomous-flow

## 高层方案

```
apps/api/zimeiti_autonomous/            # 第三包：自主运营（与 harness/api 并列）
  flows.py     五层步骤模板 + 步骤裁剪 + prompt 组装（上一步摘要作输入）
  runner.py    串行执行：逐步落记录 → 归档产出 → 失败即停
  store.py     flows / flow_runs / flow_steps 三表（幂等建表）
  router.py    /api/flows CRUD + run-now（本变更只做后端）

zimeiti_api/automations/
  store.py     kind 增加 'flow'（payload = 流程 id）
  scheduler.py 分发：flow → autonomous.runner.run_flow（经注入的入口）

app.py         set_agent_entry(harness.ask_sync) 注入 + 建表
```

## 关键决策

### D1：步骤是「五层流程的固定枚举」，不是任意 DAG
用户要的是运营链路，不是通用工作流引擎。步骤枚举
`discover|plan|produce|publish|review`，流程即「这个枚举的非空有序子集」——
配置面极小（勾选即可），语义与既有五层技能一一对应，避免过度设计成 DAG 引擎。

### D2：逐步串行的输入传递 = 上一步产出摘要
每步 prompt = 该层技能的流程指令 + 全局配置（主题/平台/是否只到草稿）+
上一步产出摘要（截断，防 token 膨胀）。完整产出不进 prompt，只落文件。

### D3：agent 入口注入，包内不 import harness
`zimeiti_autonomous` 属业务侧，但按本仓既有纪律（personas/scheduler）走注入：
`runner.set_agent_entry(fn)`；未注入时抛明确错误。分层守卫（tests/test_layering.py）
后续可把 autonomous 纳入扫描范围。

### D4：失败即停 + 如实记录（护栏不在此变更）
重试、连续失败熔断、成本上限、自主模式 HITL 放行策略都归 `autonomous-guardrails`。
本变更只保证「失败停在第 N 步、原因可见、不吞异常」——先把骨架做对，不提前做策略。

### D5：复用既有调度通道，不新起调度器
`automations/scheduler.py` 已有 cron 解析、租约防重、执行记录与归档目录约定。
新增 `kind=flow` 分发分支即可，零新机制（对齐 model-cost-rotation 复用
FallbackChatModel 的做法）。

## 风险与对策

- **风险**：长链路耗时（一步可能数十秒）→ 与既有 prompt 任务一致走
  `run_in_executor` 投线程池，不阻塞调度 tick（本变更沿用 scheduler 现成做法）
- **风险**：产出摘要过长撑爆上下文 → 摘要截断（上限字符数），完整内容只落文件
- **风险**：`publish` 步在自主模式下触发 HITL 付费门卡住 → 本变更不处理
  （护栏变更解决）；流程默认步骤集不含 publish，需用户显式勾选

## Open Questions

无。

```

## docs/openspec/changes/autonomous-flow/tasks.md

- Source: docs/openspec/changes/autonomous-flow/tasks.md
- Lines: 1-21
- SHA256: d54ef94605d6f20c2fd115f636c6d0a0b3a35433df2fb7e66f481862c15f43da

```md
---
comet_change: autonomous-flow
---

# Tasks：autonomous-flow

## 1. 包与持久化

- [ ] 1.1 建 `zimeiti_autonomous/`（flows/runner/store/router）；五层步骤枚举与裁剪校验 <!-- comet-task:5d41d363-aa40-4c4a-a6a1-ee9737e3affd -->
- [ ] 1.2 store 三表幂等建表（flows / flow_runs / flow_steps）+ CRUD 单测 <!-- comet-task:873f6b21-b809-4395-af20-1c54f8b31d52 -->

## 2. 编排执行与调度分发

- [ ] 2.1 runner 串行执行：逐步 prompt 组装（上一步摘要注入）+ 落记录 + 产出归档；单步失败即停 <!-- comet-task:b363ec57-9b8e-438b-b93d-f1211be54b59 -->
- [ ] 2.2 注入纪律：set_agent_entry（未注入显式报错）+ 包内不 import harness <!-- comet-task:fd8044e8-39dd-4328-af2e-61a20ecc4f7a -->
- [ ] 2.3 automations 扩展 kind=flow：scheduler 分发 + /api/flows 端点；既有 case/prompt 不回归 <!-- comet-task:20238ef8-9d25-4587-b97a-ca697fb1c402 -->

## 3. 验证

- [ ] 3.1 单测（裁剪校验/建表/逐步执行/失败即停/未注入报错）+ 端到端探针（mock 链路跑完整流程） <!-- comet-task:1e7568f6-542f-4cb5-91a7-e18a7a2143cd -->
- [ ] 3.2 make check 全绿 + E2E 63/63 不回归 <!-- comet-task:1cccd857-90bb-4da4-a3fb-e62ec00e96eb -->

```

## docs/openspec/changes/autonomous-flow/.openspec.yaml

- Source: docs/openspec/changes/autonomous-flow/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/autonomous-flow/specs/autonomous-flow/spec.md

- Source: docs/openspec/changes/autonomous-flow/specs/autonomous-flow/spec.md
- Lines: 1-51
- SHA256: f48a80dcaf4690cfb9db2bedd4b1c3492a4efa5f888730282ff8a732e9fd0df9

```md
# autonomous-flow 规格草案

## Purpose

让一个定时任务能编排并跑完整条运营流程，每步状态与产出可追溯，为「无人值守运营」
提供执行骨架。

## ADDED Requirements

### Requirement: 运营流程定义与持久化

系统 SHALL 提供运营流程（flow）定义，MUST 支持从五层运营流程中裁剪步骤集
（discover / plan / produce / publish / review 的任意非空子集），并 MUST 持久化
到 PG（幂等建表）。

#### Scenario: 定义一条「发现+选题」的每日流程
- **WHEN** 用户创建流程：名称「每日选题」，步骤 `[discover, plan]`，schedule `08:00`
- **THEN** 流程持久化成功，可查询到步骤集与调度配置

### Requirement: 流程逐步执行与记录

调度到点时系统 SHALL 按步骤顺序串行执行，MUST 为每一步落记录（状态、耗时、
产出摘要、产出文件引用），并 MUST 把每一步的完整产出归档到 `outputs/_automations/`
下以流程执行实例为名的目录。

#### Scenario: 到点跑完整链路
- **WHEN** 流程「全链路」步骤 `[discover, plan, produce, review]` 到点执行
- **THEN** 依次执行四步，上一步产出摘要作为下一步输入；每步记录状态与耗时；
  执行结束后可查到每步的产出文件

#### Scenario: 单步失败
- **WHEN** 某一步执行抛错
- **THEN** 该步标记失败并记录错误原因，流程**不再继续后续步骤**（重试与熔断由
  护栏变更负责），整体执行结果如实反映「在第 N 步失败」

### Requirement: agent 入口经组装层注入

`zimeiti_autonomous` 包 MUST NOT import harness 的 agent 入口；入口 SHALL 由
组装层通过 setter 注入（对齐 personas / scheduler 既有范式）。

#### Scenario: 未注入时显式报错
- **WHEN** runner 执行流程但组装层未注入 agent 入口
- **THEN** 立即抛「agent 入口未注入」的明确错误，而非静默或 AttributeError

### Requirement: 既有任务类型行为零变化

`kind=case` 与 `kind=prompt` 两类既有定时任务 MUST 保持原有行为。

#### Scenario: 回归
- **WHEN** 运行既有 case/prompt 任务
- **THEN** 执行路径与产出位置与变更前一致

```
