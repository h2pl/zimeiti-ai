# Why

双平台真实发布已 verified（real-account-verification 归档），但发布之后没有数据闭环：不知道哪些内容有效、无法量化 PRD 北极星指标（时间节省/产量）。运营数据仍靠人工去创作者中心/公众号后台看。需求来源：PRD 待解决问题「北极星指标的量化基线」+ 已归档变更的遗留项。

方案来源（开发铁律「禁止重复造轮子」的对标调研，2026-10-09）：

- **xiaobei `published-track`**：SQLite 单库按平台分表（`pub_wx_mp`/`pub_xhs`）、发布记录 upsert（去重键 source_folder+publish_date）、定时抓取互动数据回写、dna_id/account 关联供内容策略校准。
- **Easel 数据三层**：发布事件与时序快照**分离存储**（单一事实来源）、消费层**只读不回写**、确定性脚本做聚合（模型只写洞察）、内容生命周期分类（速爆/稳增/长尾）。

本变更合成两者：SQLite 存储（便于聚合） + 事件/快照分层与只读消费（避免同一事实两处存储）。

# What Changes

- 新增运营数据能力 `ops-metrics`：
  - 发布事件表（发布成功后落库，幂等 upsert）
  - 指标快照表（gzh 走已 vendor 的 wechat-mp-toolkit datacube 接口；xhs 走自有创作者中心 DOM 读取，不引入第三方采集项目）
  - 只读归因查询（确定性 CLI 输出结论，不回写数据）
- 新增 CLI：`python -m zimeiti_api.ops_metrics record / pull / report`
- 数据落盘 `data/metrics/published.db`（SQLite，gitignored）

# Capabilities

## Added Capabilities

- `ops-metrics`：发布事件记录、指标快照回收、只读归因查询

## Modified Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/ops_metrics.py`（新增：SQLite 数据层 + CLI）
- `apps/api/src/zimeiti_api/platforms/gzh.py`（datacube 取数入口）/ `xhs.py`（创作者中心指标解析）
- 不改动发布链路与合规/频控护栏；不引入第三方采集依赖（回避 MediaCrawler 的非商用许可证风险）
