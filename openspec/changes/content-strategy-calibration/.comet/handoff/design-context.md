# Comet Design Handoff

- Change: content-strategy-calibration
- Phase: design
- Mode: compact
- Context hash: 9c733cf418e5804162080d86ba86dfbd8a0dc0cf503babd1e4e454761f810a6a

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/content-strategy-calibration/proposal.md

- Source: openspec/changes/content-strategy-calibration/proposal.md
- Lines: 1-31
- SHA256: d0630d9b8d6095668f911a1b3514484015900027b81f9d9769f5d189f7f69443

```md
# Why

ops-metrics-collection / ops-metrics-pg 两变更打通了「发布事件 + 指标快照 + 只读归因」，但归因数据还只是躺着——**没有反哺创作**。PRD 的差异化定位「数据驱动选题」缺最后一环：把指标证据转成可执行的创作策略校准。

方案来源（开发铁律对标调研，2026-10-10）：

- **xiaobei `content-calibrator`**：四条评估铁律——①趋势优先（账号基线归一化，绝对值只作上下文）②脚本只给证据、好坏归因由 Agent 回读原文 ③先排混杂再归因（排不了的降级「观察」）④**策略更新必须用户逐条确认**（评估只产出建议）；评估报告落 `evals/*.eval.md`，按量触发（成熟记录 ≥5 条）+ `--force` 兜底
- **Easel `skill-publish-analytics`**：四维归因（发布时间/标签/内容类型/粉丝增长）+ 内容生命周期分类 + 确定性脚本算、模型写洞察

# What Changes

- 新增能力 `content-calibration`：**策略校准证据引擎**——按 (平台, 画像) 聚合 ops-metrics 数据，计算账号基线归一化指标、趋势、内容生命周期分布、发布节奏，产出评估报告（eval.md，含证据与「Agent 洞察」留位）
- 新增 CLI：`python -m zimeiti_api.ops_calibration calibrate [--platform] [--force]`
- 触发：MVP 仅 `--force` 手动（按量触发需成熟记录积累，留后续）；混杂不可排除时结论降级「观察」
- **不自动修改画像**：评估只产出建议，修改须经用户确认后另行处理（xiaobei 铁律 4）

# Capabilities

## Added Capabilities

- `content-calibration`：策略校准证据引擎（基线归一化、趋势与生命周期证据、评估报告、混杂降级）

## Modified Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/ops_calibration.py`（新增：证据引擎 + CLI）
- `docs/metrics/evals/`（评估报告输出，gitignored）
- 复用 ops_metrics（只读），不改动发布/合规/护栏链路

```

## openspec/changes/content-strategy-calibration/design.md

- Source: openspec/changes/content-strategy-calibration/design.md
- Lines: 1-59
- SHA256: a1db9a682adc345ea7dc07f23bcd90b6b0c3853cdaa348e26b4dd371b880f0fb

```md
---
comet_change: content-strategy-calibration
role: technical-design
canonical_spec: openspec
status: draft
---

# Design：content-strategy-calibration

## D0 设计来源（对标调研结论，非自创）

| 来源 | 借鉴点 |
|---|---|
| xiaobei `content-calibrator` | 四条评估铁律（趋势优先/脚本只给证据/先排混杂再归因/不自动改策略）；评估报告 `evals/*.eval.md`；`--force` 手动兜底；按量触发思想 |
| Easel `skill-publish-analytics` | 账号基线归一化；发布节奏/内容类型归因维度；确定性脚本算、模型只写洞察；内容生命周期分类 |
| 本项目 ops-metrics（ops-metrics-pg） | 数据源：publish_events / metric_snapshots / 只读归因（report 与生命周期判定已就绪，直接复用） |

## D1 校准对象映射

xiaobei 的「DNA」在本项目无对应体系——对应物为**画像的创作规则**（`profiles/*.yaml`：选题方向、内容类型、风格约束）与 topics 的 direction。校准粒度：(平台, 画像)——与 ops-metrics 的 profile 字段对齐。

## D2 证据引擎（确定性，全部单测覆盖）

输入：`MetricsDB`（只读）。输出 evidence dict：

1. **基线归一化**：对账号级指标（粉丝数、获赞与收藏等快照），归一化值 = 指标值 / 该账号历史均值（无均值时标记「基线不足」）
2. **趋势**：每个 metric 的首末值与 delta（复用 report.trend）
3. **生命周期分布**：单篇判定结果聚合（复用 classify_lifecycle）
4. **发布节奏**：事件按星期几/小时分布计数

## D3 评估报告（eval.md）

落 `docs/metrics/evals/<platform>-<profile>-<date>.eval.md`，结构（照 xiaobei evals 结构简化）：

```
# 策略校准评估：<platform> / <profile> / <date>
## 证据（脚本计算）
### 基线归一化 ### 趋势 ### 生命周期分布 ### 发布节奏
## 结论（确定性规则标注：结论 / 观察（混杂：<原因>））
## Agent 洞察（待填写）
## 建议（仅列出，不自动执行）
```

混杂规则：成熟记录（快照数≥5 且事件跨度≥3 天）不足 → 结论降级「观察」。

## D4 洞察生成（可选，后续闭环）

`--with-insights` 调用模型回读证据与原文撰写洞察（Easel「脚本算、模型写」）；MVP 报告留位即可，模型生成接入放在 hosted 创作前消费时一并做（避免本变更引入模型依赖）。

## D5 不做（Non-goals）

- 自动修改画像文件（铁律：评估只产出建议，用户确认后另行处理）
- 按量自动触发（需成熟记录积累，MVP 仅 --force）
- 多账号聚合对比（单账号起步）

## D6 测试策略

- 单测：证据引擎（归一化/趋势/节奏/只读）、报告结构（证据与洞察分离）、混杂降级、CLI
- 真账号走查：用已回收的真实数据生成校准报告并人工检视

```

## openspec/changes/content-strategy-calibration/tasks.md

- Source: openspec/changes/content-strategy-calibration/tasks.md
- Lines: 1-14
- SHA256: 321e78bc41d5a618020ac6599dc346c9889027ce1f3fceede5e1fde749a947d3

```md
# Tasks

## 1. 证据引擎

- [ ] 1.1 证据计算：基线归一化 / 趋势 / 生命周期分布 / 发布节奏（复用 MetricsDB 只读）；验证：单测覆盖四类证据与只读不回写 <!-- comet-task:4604e131-ee5e-4be3-80cc-a629548708fb -->
- [ ] 1.2 评估报告生成：eval.md（证据 + 结论降级标注 + 洞察留位 + 建议章节）；验证：单测断言结构与混杂降级 <!-- comet-task:a354462b-39f6-4fbc-9de9-2da5b304d65d -->

## 2. CLI 与真账号走查

- [ ] 2.1 CLI calibrate（--platform/--profile/--force）+ 真账号走查：用已回收真实数据生成报告并人工检视；验证：报告落盘 + 人工检视通过 <!-- comet-task:867cf477-dc81-4c11-9c7c-d280c460c11f -->

## 3. 收尾

- [ ] 3.1 验证报告增补；验证：文档与证据一致 <!-- comet-task:da4e906a-3033-48be-9aa5-f8286c97b79c -->

```

## openspec/changes/content-strategy-calibration/.openspec.yaml

- Source: openspec/changes/content-strategy-calibration/.openspec.yaml
- Lines: 1-2
- SHA256: e61703315c59969805e021ec521ca189369aaf8ea902d52c5e39c7fbc603598f

```md
schema: spec-driven
created: 2026-10-10

```

## openspec/changes/content-strategy-calibration/specs/content-calibration/spec.md

- Source: openspec/changes/content-strategy-calibration/specs/content-calibration/spec.md
- Lines: 1-37
- SHA256: 8b6133b210c0f55604353fb42b89c364485df397801e4d4da37b66666357e698

```md
# 内容策略校准（证据引擎与评估报告）

## ADDED Requirements

### Requirement: 策略评估证据生成
系统 MUST 按 (平台, 画像) 维度聚合 ops-metrics 的发布事件与指标快照，输出确定性校准证据：账号基线归一化指标（各指标相对该账号均值的比值，绝对值仅作上下文）、指标趋势（首末对比）、内容生命周期分布（速爆型/稳增型/长尾型占比）、发布节奏（按日/周分布）。证据计算 MUST 为确定性脚本逻辑，聚合结果 MUST 可复现。

#### Scenario: 生成校准证据
- **GIVEN** 存在某平台的发布事件与多次指标快照
- **WHEN** 执行校准命令
- **THEN** 输出包含基线归一化指标、趋势、生命周期分布与发布节奏，且重复执行结果一致

#### Scenario: 只读
- **GIVEN** 执行校准命令
- **WHEN** 证据生成完成
- **THEN** ops-metrics 的事件与快照数据保持不变

### Requirement: 评估报告与证据/洞察分离
校准 MUST 产出评估报告（eval.md），报告 MUST 包含：确定性证据（脚本计算）、账号基线说明、以及留给 Agent 的「洞察」章节（由 Agent 回读证据与内容原文后撰写）。脚本 MUST NOT 输出好坏归因结论——归因是 Agent 的职责。存在无法排除的混杂因素（如账号成熟度低、样本量不足）时，相关结论 MUST 降级标记为「观察」而非「结论」。

#### Scenario: 报告含证据与洞察留位
- **GIVEN** 校准证据生成完成
- **WHEN** 生成评估报告
- **THEN** 报告含确定性证据章节与「Agent 洞察（待填写）」章节，且证据数值与引擎输出一致

#### Scenario: 混杂降级
- **GIVEN** 该平台成熟记录不足 5 条或账号发布不足 3 天
- **WHEN** 生成报告
- **THEN** 报告将策略性结论标记为「观察（混杂：样本不足）」，不冒充结论

### Requirement: 评估产出建议不自动改画像
评估报告 MAY 包含策略建议（如调整选题方向、发布节奏），但系统 MUST NOT 自动修改画像文件；画像调整 MUST 经用户确认后另行处理。

#### Scenario: 报告仅产出建议
- **GIVEN** 评估报告生成完成
- **WHEN** 检查画像文件
- **THEN** 画像文件未被修改

```
