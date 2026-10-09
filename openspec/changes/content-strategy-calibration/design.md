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
