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
