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
