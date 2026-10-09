# Comet Design Handoff

- Change: ops-metrics-report
- Phase: design
- Mode: compact
- Context hash: c75dc8a49858403ffb0e8f4652a0ecbc98029b91bac91c7dff9b07e16475694a

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/ops-metrics-report/proposal.md

- Source: openspec/changes/ops-metrics-report/proposal.md
- Lines: 1-25
- SHA256: 0c1f0772a82bcd1ff801725a30d7783089def3af20ae5efc5ed44af384b084f6

```md
# Why

ops-metrics（数据回收）与 content-strategy-calibration（校准报告）的数据目前只有 markdown/JSON 形态，运营者需要一个一眼可读的可视化报告页。对标 Easel `data-report`（确定性脚本：KPI 卡 + 图表 + 数据表 → 自包含 HTML，模型只写洞察），为本项目生成运营数据 HTML 报告页。

# What Changes

- 新增 `ops_report_page.py`：从 ops-metrics PG 数据确定性生成**自包含 HTML 报告页**（KPI 卡 + 内联 SVG 图表 + 发布事件表 + 洞察区）
- 新增 CLI：`python -m zimeiti_api.ops_report_page [--platform] [-o 输出路径]`
- 图表用内联 SVG（零新增依赖）；与 Easel 的差异（matplotlib/base64）在 design 注明：本项目图表类型简单（趋势线/柱状），SVG 足够且零依赖
- xhs 单篇明细指标不在本变更（列语义待人工比对，范围收敛）

# Capabilities

## Modified Capabilities

- `ops-metrics`：ADDED Requirement 运营数据报告页（自包含 HTML，确定性生成，含 KPI/图表/事件表）

## Added Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/ops_report_page.py`（新增）
- 零依赖变更；不触碰发布链路

```

## openspec/changes/ops-metrics-report/design.md

- Source: openspec/changes/ops-metrics-report/design.md
- Lines: 1-25
- SHA256: 1a87b8bf873132c5be959c06d6a243c05d45cb1b8ccfeed13a28b31cdd6df1b0

```md
---
comet_change: ops-metrics-report
role: technical-design
canonical_spec: openspec
status: draft
---

# Design：ops-metrics-report

## D0 设计来源

**Easel `data-report`**：确定性脚本（数据读取、聚合、出图、HTML 组装全部脚本完成），产出自包含 HTML（KPI 卡 + 图表 + 数据表），模型只写洞察文字；两步法（analyze 概览 → report 生成）。图表自动选型：时间序列→折线、类别→柱状。

## D1 实现

- `ops_report_page.py`：`render_html_report(db, platform=None) -> str`（HTML 字符串）+ CLI 写文件
- KPI 卡：最新粉丝数/获赞与收藏（xhs 账号级快照）、事件数、快照数、生命周期分布
- 图表（内联 SVG，零依赖）：各 metric 快照趋势折线、生命周期柱状、发布节奏柱状
- 数据表：publish_events 全量行
- 洞察区：引用校准 eval 报告路径（若存在）+ 留位
- 与 Easel 差异：图表 SVG 而非 matplotlib+base64（本项目图表类型简单：一条趋势线/两根柱状，零新增依赖；Easel 方案适用于复杂数据集）；数据源为 ops-metrics PG 而非 CSV

## D2 测试

- 单测：KPI 数值、SVG 存在、事件表行数、无数据指标显示「无数据」、只读

```

## openspec/changes/ops-metrics-report/tasks.md

- Source: openspec/changes/ops-metrics-report/tasks.md
- Lines: 1-10
- SHA256: 3ecffffa4b50fa7c48c6d3f809ae640b58b74ce1875f3e10162908179815459a

```md
# Tasks

## 1. 报告页生成

- [ ] 1.1 render_html_report：KPI 卡 + SVG 图表（趋势/生命周期/节奏）+ 事件表 + 洞察区（无数据显示「无数据」）；验证：单测覆盖结构与数值、只读 <!-- comet-task:bf972472-aa3f-43c0-849c-1ab02bdcc75e -->
- [ ] 1.2 CLI（--platform/-o）+ 真账号数据生成报告页；验证：报告可离线打开且数值一致 <!-- comet-task:9b067058-efbc-47e7-9308-d1436b2cf703 -->

## 2. 收尾

- [ ] 2.1 验证报告增补；验证：文档与证据一致 <!-- comet-task:7c60269a-7290-4361-b770-cccf98b587c2 -->

```

## openspec/changes/ops-metrics-report/.openspec.yaml

- Source: openspec/changes/ops-metrics-report/.openspec.yaml
- Lines: 1-2
- SHA256: e61703315c59969805e021ec521ca189369aaf8ea902d52c5e39c7fbc603598f

```md
schema: spec-driven
created: 2026-10-10

```

## openspec/changes/ops-metrics-report/specs/ops-metrics/spec.md

- Source: openspec/changes/ops-metrics-report/specs/ops-metrics/spec.md
- Lines: 1-21
- SHA256: 525e745eb6aa5a0ca53a263de8e554b531133b07d17e24c2b52f465b5eb9bbe6

```md
# 运营数据（报告页）

## ADDED Requirements

### Requirement: 运营数据报告页
系统 MUST 能从运营数据（发布事件、指标快照）确定性生成自包含 HTML 报告页，包含：KPI 卡（最新粉丝数、获赞与收藏、事件数、快照数、生命周期分布）、趋势图表（SVG）、发布事件表与洞察区。生成 MUST 为只读（不修改数据），文件 MUST 可离线打开（无外部资源依赖）。缺数据的指标 MUST 显示「无数据」而非零值。

#### Scenario: 生成报告页
- **GIVEN** 存在发布事件与指标快照
- **WHEN** 生成报告页
- **THEN** 输出自包含 HTML，含 KPI 卡、SVG 图表、事件表，数值与数据源一致

#### Scenario: 无数据显示而非零值
- **GIVEN** 某指标无任何快照
- **WHEN** 生成报告页
- **THEN** 该指标显示「无数据」

#### Scenario: 生成只读
- **GIVEN** 生成报告页
- **WHEN** 完成
- **THEN** 事件与快照数据保持不变

```
