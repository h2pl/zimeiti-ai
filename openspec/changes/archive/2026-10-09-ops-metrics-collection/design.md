---
comet_change: ops-metrics-collection
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-09-ops-metrics-collection
status: final
---

# Design：ops-metrics-collection

## D0 设计来源（对标调研结论，非自创）

| 借鉴来源 | 借鉴点 |
|---|---|
| xiaobei `published-track` | SQLite 单库按平台分表；发布记录 upsert（去重键 source_folder+publish_date）；dna_id/account 关联供策略校准 |
| Easel 数据三层 | 发布事件 vs 时序快照**分离表存储**（单一事实来源）；消费层**只读不回写**；确定性脚本聚合、模型只写洞察；内容生命周期分类（速爆/稳增/长尾） |

## D1 数据模型（SQLite，借鉴 xiaobei 分表 + Easel 分层）

```
data/metrics/published.db
├── publish_events      # 发布事件（Easel 的 publish-log 层）
│     id, platform, title, content_type, source_folder, publish_url,
│     publish_date, profile, topic_direction, status(ok|failed), notes,
│     created_at, updated_at
│     UNIQUE(platform, source_folder, publish_date)   # upsert 去重键（xiaobei）
├── metric_snapshots    # 时序快照（Easel 的 snapshots 底座）
│     id, platform, event_id, metric, value, captured_at, source(datacube|creator-center)
├── collection_errors   # 采集失败留痕（对应 spec「失败保留历史」）
│     id, platform, scope, error, occurred_at
```

指标以**窄表**（metric/value 行）而非每平台宽表：平台指标项差异大、且会随站点改版增减，窄表避免频繁改 schema（对 Easel 快照 JSON 的改进：JSON 灵活但难聚合；对 xiaobei 宽表的改进：宽表需按平台建表迁移）。

## D2 取数实现

- **gzh**：`platforms/gzh.py` 新增 datacube 取数入口，直接调用**已 vendor** 的 `wechat_mp.client` datacube 方法（`get_user_summary` / `get_user_read` / `get_article_read` / `get_article_share`），零新增协议代码
- **xhs**：`platforms/xhs.py` 复用现有 `_open_page` 登录态打开创作者中心首页，解析**数据看板**的「标签→值」文本对（曝光数/观看数/点赞数/评论数/收藏数/分享数/净涨粉/新增关注/取消关注，含近 7 日/近 30 日周期切换）与账号概览（关注数/粉丝数/获赞与收藏）
  - **不引入第三方采集项目**：MediaCrawler（46k stars）许可证为 NON-COMMERCIAL LEARNING LICENSE 1.1，与 PRD 订阅 SaaS 商业化路径冲突，故不采用
  - **单篇明细不采集（范围收敛）**：笔记管理页每篇的 5 个数字列**无列头文本、无 title 属性**（仅 svg 图标 + 数字），列语义无法可靠确定；按零假阳性铁律不猜列序，改为只采集账号级指标。待真账号走查人工比对列序后，留作后续变更

## D3 只读消费

`ops_metrics report` 输出：按平台/画像的趋势、单篇内容生命周期判定（速爆型/稳增型/长尾型，判定规则确定性实现）。全程只读，不回写任何事件/快照（Easel 铁律）。

## D4 不做（Non-goals）

- 可视化报告页面（Easel `data-report` 的 HTML 报告—后续如需单独立变更）
- 自动选题策略改写（消费方，非本变更）
- 第三方采集框架集成（许可证冲突，见 D2）
- 定时调度（先手工/托管循环触发，定时任务后续）

## D5 风险与对策

| 风险 | 对策 |
|---|---|
| xhs 创作者中心列序改版 | 按列头文本映射指标名，列缺失时记录 collection_errors 而非写零 |
| gzh datacube 日期跨度限制（部分接口≤7天） | 取数按接口限制分档，越界时显式报错 |
| 登录态失效 | 复用现有失效引导流程，采集失败落 collection_errors |

## D6 测试策略

- 单测：事件 upsert、快照写入、失败保留历史、xhs 列解析、gzh datacube 解析（mock）
- 真账号走查：真实回收一次双平台数据并人工比对后台数值
