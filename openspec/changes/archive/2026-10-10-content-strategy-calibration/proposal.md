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
