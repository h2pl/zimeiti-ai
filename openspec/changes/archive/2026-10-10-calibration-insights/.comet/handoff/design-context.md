# Comet Design Handoff

- Change: calibration-insights
- Phase: design
- Mode: compact
- Context hash: a2859966e759b723a6905a8c5f69fe756fd9f2ecd9d8806397e8ef3e8ee8f312

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/calibration-insights/proposal.md

- Source: openspec/changes/calibration-insights/proposal.md
- Lines: 1-24
- SHA256: 546d4f7aa60b5a976295d0b34a8abf76e0765edf7d3c5176427ca83acfee3426

```md
# Why

content-strategy-calibration（已归档）产出的校准报告只有证据与留位，「Agent 洞察」无人填写；且校准仅手动触发。对标 Easel `skill-publish-analytics` 后发现其「关键发现」由**确定性脚本**按数据排名生成（Top 3 可执行洞察 + 方法论 + 局限性声明），模型完全不在链路里——比引入 LLM 更简单、可单测、零成本。本变更补齐：关键发现生成、方法论/局限性章节、按量触发（--auto）与定时入口。

# What Changes

- `ops_calibration.py` 新增：关键发现生成（确定性排名：最佳生命周期类型/发布日/基线异常指标）、方法论与局限性章节、`--auto` 按量触发（自上次校准以来新快照 ≥5 才执行，否则输出跳过原因）
- 评估报告新增「关键发现」「方法论」「局限性」三章节
- 不引入模型依赖；Agent 洞察章保留留位（托管循环的 Agent 填写）

# Capabilities

## Modified Capabilities

- `content-calibration`：校准报告 MUST 含确定性「关键发现」（Top 3 可执行洞察）、方法论与局限性章节；MUST 支持按量触发（自上次校准以来新快照 ≥5）

## Added Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/ops_calibration.py`（扩展）
- `apps/api/tests/test_ops_calibration.py`（新增用例）

```

## openspec/changes/calibration-insights/design.md

- Source: openspec/changes/calibration-insights/design.md
- Lines: 1-40
- SHA256: ec5084962073c98348f8ea7b74182a7e13a23a15e25dbd5890691dfdb7958bd8

```md
---
comet_change: calibration-insights
role: technical-design
canonical_spec: openspec
status: draft
---

# Design：calibration-insights

## D0 设计来源

**Easel `skill-publish-analytics`**：关键发现由确定性脚本按数据排名生成（Top 3 可执行洞察），报告含方法论与局限性声明（样本量/null 覆盖率/「关联性不等于因果性」）。**xiaobei**：`--force` 手动兜底 + 按量触发思想（成熟记录阈值）。

## D1 关键发现生成（确定性规则，全部单测覆盖）

从 evidence 排名产出至多 3 条可执行洞察：

1. **生命周期结构**：占比最高的类型及其含义（如「长尾型 N%——内容生命周期长，优先维护旧文」）
2. **最佳发布日**：事件最多的星期几（≥2 篇才纳入，否则跳过）
3. **基线异常**：归一化值偏离 1 最大的账号级指标（≥2 点快照才纳入；normalized ≥1.5 或 ≤0.5 报告偏离方向）

证据不足（无快照/无事件）时不编造，输出「数据不足」。

## D2 方法论与局限性章节（固定结构 + 动态数值）

方法论：互动/基线计算公式说明。局限性：样本量、快照覆盖、「关联性不等于因果性」声明（照抄 Easel 措辞思路）。

## D3 按量触发

上次校准时间戳：eval 报告文件名日期（简单可靠）。--auto 时统计「新快照」= captured_at 晚于上次校准日的快照数；≥5 → 执行；<5 → 返回 skipped{count, threshold}，exit 0，不生成报告。--force 绕过。

## D4 定时入口

`auto` 子命令即定时入口（cron/heartbeat 调 `python -m zimeiti_api.ops_calibration auto --platform ...`）。不内置调度器（系统 cron/托管 heartbeat 负责触发，各司其职）。

## D5 测试

- 关键发现三条规则各一用例 + 证据不足不编造
- --auto 达标/未达标/force 绕过
- 报告含方法论/局限性章节

```

## openspec/changes/calibration-insights/tasks.md

- Source: openspec/changes/calibration-insights/tasks.md
- Lines: 1-14
- SHA256: bc3340fd96190361a904e4b8977f791cdae105124a52988984a91983891f307f

```md
# Tasks

## 1. 关键发现与报告扩展

- [ ] 1.1 关键发现生成（生命周期结构/最佳发布日/基线异常三条规则，证据不足不编造）；验证：单测覆盖三条规则与数据不足分支 <!-- comet-task:5b03a7e0-9c3c-400b-b9e9-b186b7cbb434 -->
- [ ] 1.2 报告扩展「关键发现」「方法论」「局限性」章节；验证：单测断言章节与动态数值 <!-- comet-task:0f67e8a1-8ba2-4828-ba94-7850d4f15f5b -->

## 2. 按量触发

- [ ] 2.1 --auto 按量触发（新快照 ≥5 执行，否则 skipped 原因；--force 绕过）+ auto 子命令定时入口；验证：单测覆盖达标/未达标/force <!-- comet-task:81ad5660-5826-4862-9748-834c1b70eee9 -->

## 3. 收尾

- [ ] 3.1 验证报告增补；验证：文档与证据一致 <!-- comet-task:341178f6-0822-44c7-9d17-844d533369c9 -->

```

## openspec/changes/calibration-insights/.openspec.yaml

- Source: openspec/changes/calibration-insights/.openspec.yaml
- Lines: 1-2
- SHA256: e61703315c59969805e021ec521ca189369aaf8ea902d52c5e39c7fbc603598f

```md
schema: spec-driven
created: 2026-10-10

```

## openspec/changes/calibration-insights/specs/content-calibration/spec.md

- Source: openspec/changes/calibration-insights/specs/content-calibration/spec.md
- Lines: 1-36
- SHA256: d7f8eb9cd233a58a2d7339da0888faae8944221c49642ae6759e294892922b30

```md
# 内容策略校准（关键发现与按量触发）

## MODIFIED Requirements

### Requirement: 评估报告与证据/洞察分离
校准 MUST 产出评估报告（eval.md），报告 MUST 包含：确定性证据（脚本计算）、**关键发现（确定性脚本按数据排名生成 Top 3 可执行洞察）、方法论与局限性章节**、账号基线说明、以及留给 Agent 的「洞察」章节（由 Agent 回读证据与内容原文后撰写）。脚本 MUST NOT 输出好坏归因结论——归因是 Agent 的职责。存在无法排除的混杂因素（如账号成熟度低、样本量不足）时，相关结论 MUST 降级标记为「观察」而非「结论」。

#### Scenario: 报告含证据与洞察留位
- **GIVEN** 校准证据生成完成
- **WHEN** 生成评估报告
- **THEN** 报告含确定性证据章节与「Agent 洞察（待填写）」章节，且证据数值与引擎输出一致

#### Scenario: 混杂降级
- **GIVEN** 该平台成熟记录不足 5 条或账号发布不足 3 天
- **WHEN** 生成报告
- **THEN** 报告将策略性结论标记为「观察（混杂：样本不足）」，不冒充结论

#### Scenario: 关键发现由脚本确定性生成
- **GIVEN** 校准证据包含趋势、生命周期分布与发布节奏
- **WHEN** 生成评估报告
- **THEN** 报告「关键发现」章节含至少一条基于数据排名的可执行洞察（如最佳发布日、生命周期占比、基线异常），并附「方法论」与「局限性」（样本量、混杂声明）章节

## ADDED Requirements

### Requirement: 按量触发校准
校准 MUST 支持按量触发模式（--auto）：自上次校准以来新收集的快照数 ≥5 时执行校准，否则输出跳过原因（含当前计数）且 MUST NOT 生成新报告；--force 手动触发 MUST 绕过该检查。

#### Scenario: 达到阈值自动执行
- **GIVEN** 自上次校准以来新收集快照 ≥5
- **WHEN** 以 --auto 模式执行校准
- **THEN** 正常生成报告

#### Scenario: 未达阈值跳过
- **GIVEN** 自上次校准以来新收集快照 <5
- **WHEN** 以 --auto 模式执行校准
- **THEN** 不生成新报告，输出跳过原因与当前计数

```
