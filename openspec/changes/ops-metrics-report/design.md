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
