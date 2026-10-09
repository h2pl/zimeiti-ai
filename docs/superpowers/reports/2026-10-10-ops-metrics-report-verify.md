# 验证报告（Verify Report）——变更 ops-metrics-report

- 日期：2026-10-10
- 分支：comet/ops-metrics-report
- 范围：运营数据 HTML 报告页（Easel data-report 对标，确定性生成自包含 HTML）

## 结论

**通过（Go）**——双平台报告页真实生成，KPI 与 PG 数据一致，自包含可离线打开：
- xhs-main：KPI 粉丝 212 / 获赞与收藏 5281 ✓，SVG 图表 2 处，无外部资源依赖 ✓
- gzh-main：无账号级快照指标显示「无数据」✓（零假阳性），failed 事件状态标红 ✓
- 门禁：make check 85 passed 全绿

## 校验记录

| 项 | 结果 | 证据 |
|---|---|---|
| KPI 一致性 | 粉丝 212 / 获赞与收藏 5281 与 PG 一致 | tests/test_ops_report_page.py + 真实报告 |
| 自包含 | 无 http(s):// 外部依赖 | 单测断言 |
| 只读 | 生成前后快照不变 | 单测 |
| 平台过滤 | gzh 报告不含 xhs 事件 | 单测 |
| 缺数据显示 | 「无数据」而非零值 | 单测 |
| 真账号生成 | 双平台 report-*.html 落盘 | data/metrics/ |

## 设计差异记录（vs Easel data-report）

- 图表用内联 SVG 而非 matplotlib+base64：本项目图表类型简单（趋势折线/柱状），零新增依赖；Easel 方案适用于复杂数据集
- 数据源 ops-metrics PG 而非 CSV

## 遗留

1. 图表交互（tooltip 已有 title，可加 hover 高亮）
2. 报告页定时生成接线（cron/heartbeat 调 CLI 即可）
