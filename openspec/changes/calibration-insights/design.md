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
