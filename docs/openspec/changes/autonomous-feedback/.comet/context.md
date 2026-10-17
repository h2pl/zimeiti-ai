# Comet Design Handoff

- Change: autonomous-feedback
- Phase: design
- Mode: compact
- Context hash: d3906c851b9f1ac6dc1914de5151331a816ac7cc60e64052bc5047c4c3bea861

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/autonomous-feedback/proposal.md

- Source: docs/openspec/changes/autonomous-feedback/proposal.md
- Lines: 1-52
- SHA256: ae521ee59f178262bd374b28512bfc8a4976b32703dbc6ce50b4a8d814fb6f11

```md
---
comet_change: autonomous-feedback
---

# autonomous-feedback：发布数据回流，校准下一轮选题

## Why

自主运营闭环的第二环。现状盘点（grep 级）：

- **已有发布事实**：`content/ops_analytics.py` 把发布/草稿创建成功的最小记录落到
  `outputs/_analytics/<platform>/<date>.json`（按 media_id 幂等）——「发布过什么」是有的
- **已有数据抓取**：`platforms/analytics.py`（登录态跑脚本取平台创作数据）
- **缺口（关键）**：这些事实**没有回流**。复盘层（review）的结论只停留在当次执行里，
  下一轮 discover 步仍从零开始找热点——链路跑得再顺也不是闭环，只是重复执行

xiaobei 的对应能力是 `published-track`（发布记录追踪）+ `content-calibrator`
（消费表现数据做校准）；本变更不搬其实现（SQLite + bash + openclaw 绑定），
用 zimeiti 已有的文件源 + 五层流程实现。

## What Changes

- `zimeiti_autonomous/feedback.py`：
  - `collect_published()`：汇总发布事实（按平台/时间窗，读既有 `outputs/_analytics/`）
  - `build_calibration()`：把事实汇总成**校准信号**（哪些类型发过、近期密度、
    待补缺口；无数据时如实报告，不虚构表现）
  - `context_for_discover()`：校准信号的文本形态，供 discover 步注入
- 接 ① 的编排层：`flows.build_step_prompt` 支持 `feedback` 段；`runner` 在
  **discover 步**自动注入校准信号（其余步骤不受影响）
- 归档：`outputs/_feedback/<date>.md` 落一份当次校准结论，便于追溯与人工查看
- API：`GET /api/feedback`（最近一次校准信号，供前端后续看板消费）

## Non-Goals

- **不做平台阅读数拉取**（需凭据与定时任务）：沿用 ops_analytics 既定决策 D2——
  先落「发布事实」，有表现数据则消费，没有则如实报告
- **不做评分/排序模型**：校准信号是事实摘要 + 缺口提示，不做机器学习式打分
- **不做无人值守护栏**（重试/熔断/成本上限）：`autonomous-guardrails`
- **不做前端看板**：`autonomous-observability`

## Capabilities

### New Capabilities

- `autonomous-feedback`：发布事实回流成校准信号并注入发现层，运营链路具备
  「上一轮影响下一轮」的闭环能力；无数据时如实降级

## Impact

`zimeiti_autonomous` 包新增 `feedback.py`；`flows.py` / `runner.py` 增加可选
feedback 注入；新增 `/api/feedback` 与 `outputs/_feedback/` 归档目录。
既有流程行为在「无发布事实」时与变更前一致（降级为空校准段）。

```

## docs/openspec/changes/autonomous-feedback/design.md

- Source: docs/openspec/changes/autonomous-feedback/design.md
- Lines: 1-58
- SHA256: ad38b786e79001ad84a07b711c0b59bfb7a1501e5ccdf32b77a345b2489282ed

```md
---
comet_change: autonomous-feedback
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：autonomous-feedback

## 高层方案

```
zimeiti_autonomous/feedback.py
  collect_published(days=14)  读 outputs/_analytics/<platform>/<date>.json → 事实列表
                              （源缺失/坏 JSON → 空列表；不虚构）
  build_calibration(items)    事实 → 校准信号文本：发过什么、密度、待补缺口
                              （无事实 → 如实「暂无发布记录」）
  context_for_discover()      汇总 + 归档 outputs/_feedback/<date>.md → 返回文本

flows.build_step_prompt(step, config, prev_summary, feedback="")
  仅当 step == discover 且 feedback 非空时追加校准段
runner.run_flow：discover 步执行前调 feedback.context_for_discover()（可关闭）
router：GET /api/feedback
```

## 关键决策

### D1：只读既有文件源，不新增表
`ops_analytics.py` 已经把发布事实落到文件（按 media_id 幂等）。再建一张 PG 表是
重复数据源、且要处理双写一致。校准是**读侧汇总**，读文件即可——与 xiaobei 的
`published-track`（SQLite）相比，这里的既有事实源已经存在，没必要另起炉灶。

### D2：校准信号只陈述事实与缺口，不做评分
不做「表现打分/推荐权重」——那需要真实表现数据（阅读数等），而项目既定决策是
先不拉。信号形态：`发过 N 条（平台分布）→ 最近一次 X 天前 → 建议补缺口 Y`。
诚实优先：没有表现数据就只说事实，不编造 CTR/阅读数。

### D3：注入只作用于 discover 步
闭环的意义是「上一轮影响下一轮的选题」。produce/publish 步注入校准段只会污染
上下文且有跑题风险；review 步自己就在产出结论。故仅 discover 注入（D3 与规格一致）。

### D4：feedback 可关闭（配置 `feedback: false`）
探针与单测需要确定性；部分流程（如纯复盘流程）不需要校准段。配置面留一个开关，
默认开。

### D5：归档到人可读的 Markdown
`outputs/_feedback/<date>.md`——既能被 agent 后续读取，也能被人直接打开看，
比 JSON 更契合「运营」场景。

## 风险与对策

- **风险**：analytics 文件结构演进（字段变化）→ 解析用 `.get` 容错，坏文件跳过并计数
- **风险**：时间窗内文件很多（大量发布）→ 汇总只取条数与最近若干条标题，截断上限
- **风险**：注入使 discover 步 prompt 变长 → 校准段限长（与摘要同量级），可关闭

## Open Questions

无。

```

## docs/openspec/changes/autonomous-feedback/tasks.md

- Source: docs/openspec/changes/autonomous-feedback/tasks.md
- Lines: 1-20
- SHA256: 532f7d729fb570521e14ee70a107204c9fc39a672feb880c191d09168516dded

```md
---
comet_change: autonomous-feedback
---

# Tasks：autonomous-feedback

## 1. 汇总与校准

- [ ] 1.1 feedback.collect_published：读 outputs/_analytics，按平台/时间窗聚合；源缺失或坏 JSON → 空列表不报错 <!-- comet-task:103b7118-0aa9-430a-9ee0-4ee2630f1090 -->
- [ ] 1.2 build_calibration：事实 → 校准信号（只陈述事实与缺口，无数据如实报告）+ 归档 outputs/_feedback/<date>.md <!-- comet-task:b003fba7-53aa-40b6-b8bf-cbbd86ada65e -->

## 2. 注入发现层

- [ ] 2.1 flows.build_step_prompt 支持 feedback 段（仅 discover 注入）+ runner 在 discover 步调用（可关闭） <!-- comet-task:4cc3ef81-799f-43a5-adf9-cd3c5acb2cba -->
- [ ] 2.2 GET /api/feedback 暴露最近校准信号 <!-- comet-task:cf220eb1-c7f1-45d3-8679-52503649fc03 -->

## 3. 验证

- [ ] 3.1 单测（有事实汇总/无事实降级/坏文件容错/仅 discover 注入/归档落盘）+ 探针（造样本→跑流程→断言校准段） <!-- comet-task:9ef31df4-dc51-40f3-afdf-9fb281e4bdb8 -->
- [ ] 3.2 make check 全绿 + E2E 63/63 不回归 <!-- comet-task:6532348a-848e-4d38-a2d1-3dd4453ebe13 -->

```

## docs/openspec/changes/autonomous-feedback/.openspec.yaml

- Source: docs/openspec/changes/autonomous-feedback/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/autonomous-feedback/specs/autonomous-feedback/spec.md

- Source: docs/openspec/changes/autonomous-feedback/specs/autonomous-feedback/spec.md
- Lines: 1-44
- SHA256: 43d3948cefa47a522438955d40720184f86513d4dfc9b482720028974b7d0e81

```md
# autonomous-feedback 规格草案

## Purpose

把已发布事实汇总成校准信号并注入发现层，让运营链路具备「上一轮影响下一轮」的
闭环；数据缺失时如实降级，绝不虚构表现。

## ADDED Requirements

### Requirement: 发布事实汇总

系统 SHALL 汇总既有发布事实（`outputs/_analytics/<platform>/<date>.json`），
MUST 按平台与时间窗聚合，并 MUST 在源缺失或不可解析时返回空结果（不报错、不虚构）。

#### Scenario: 有发布事实
- **WHEN** `outputs/_analytics/wechat/2026-10-18.json` 存在且含两条记录
- **THEN** 汇总结果含平台 wechat、条数 2、标题/时间等事实字段

#### Scenario: 无发布事实
- **WHEN** `outputs/_analytics/` 不存在或为空
- **THEN** 汇总返回空列表，校准信号如实说明「暂无发布记录」，不编造任何表现数据

### Requirement: 校准信号注入发现层

`runner` 在执行 **discover 步**时 SHALL 注入校准信号到该步 prompt；其余步骤
MUST NOT 受此影响。校准信号 MUST 只陈述事实与缺口提示，不得包含虚构的表现数值。

#### Scenario: 注入可观测
- **WHEN** 流程含 discover 步且存在发布事实
- **THEN** discover 步的入参 prompt 含校准段（含平台与条数事实），且 produce 步的
  prompt 不含该段

#### Scenario: 无数据时降级
- **WHEN** 无发布事实
- **THEN** discover 步 prompt 的校准段如实写「暂无发布记录」，流程正常执行

### Requirement: 校准结论归档

系统 SHALL 把每次生成的校准信号归档到 `outputs/_feedback/<date>.md`，并 SHALL
通过 `GET /api/feedback` 暴露最近一次校准信号。

#### Scenario: 归档与查询
- **WHEN** 生成校准信号后
- **THEN** `outputs/_feedback/<date>.md` 存在且 `GET /api/feedback` 返回其内容摘要

```
