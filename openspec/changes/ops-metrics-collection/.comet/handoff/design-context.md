# Comet Design Handoff

- Change: ops-metrics-collection
- Phase: design
- Mode: compact
- Context hash: 24523baaa6ce16c29b7bd74362052c6396c0fe78bd012492b0bd76e2624bc6d5

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/ops-metrics-collection/proposal.md

- Source: openspec/changes/ops-metrics-collection/proposal.md
- Lines: 1-35
- SHA256: addf1f02cf56b445a9bb761090d3a3776b1f358a0071342beffbced5f7b42d65

```md
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

```

## openspec/changes/ops-metrics-collection/design.md

- Source: openspec/changes/ops-metrics-collection/design.md
- Lines: 1-63
- SHA256: 3a392c823cca9f96ea0eca2cd27a4715da4433c268f5e32ebaae13ac190c2360

```md
---
comet_change: ops-metrics-collection
role: technical-design
canonical_spec: openspec
status: draft
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

```

## openspec/changes/ops-metrics-collection/tasks.md

- Source: openspec/changes/ops-metrics-collection/tasks.md
- Lines: 1-19
- SHA256: 37b9dbe7d01036fcc3818061f4a5d7b931c8306f6ebe6c92f54e1cc17e8846e6

```md
# Tasks

## 1. 数据层

- [ ] 1.1 SQLite 数据层：publish_events / metric_snapshots / collection_errors 三表 + upsert 去重键（platform+source_folder+publish_date）+ 失败留痕；验证：单测覆盖幂等 upsert 与失败不覆盖历史 <!-- comet-task:8d8c204c-c3b9-4bc2-8fe5-dc688914368f -->
- [ ] 1.2 gzh datacube 取数入口：调用已 vendor 的 wechat_mp.client datacube 方法，写入快照（source=datacube）；验证：单测 mock 解析 + 日期跨度越界显式报错 <!-- comet-task:395260eb-f627-4aad-8eee-6120a3a7ae12 -->
- [ ] 1.3 xhs 数据看板取数：复用登录态解析创作者中心首页「标签→值」文本对（曝光/观看/点赞/评论/收藏/分享/净涨粉等）+ 账号概览；验证：单测覆盖标签解析与缺失标签落 collection_errors <!-- comet-task:75778886-c690-4d6f-92c2-1f9046edacde -->

## 2. 只读消费

- [ ] 2.1 归因查询（只读）：按平台/画像趋势 + 单篇内容生命周期判定（速爆/稳增/长尾，确定性规则）；验证：单测断言查询结果且数据不回写 <!-- comet-task:eee6978a-b4aa-4895-bd7c-1433e6896c4d -->

## 3. 真账号走查

- [ ] 3.1 双平台真实取数一次并与后台数值人工比对；验证：快照落盘 + 人工核对一致（并人工确认笔记管理页 5 列数字语义，供后续单篇指标变更） <!-- comet-task:563f8837-3e25-4909-9ddf-7c12db00f8f4 -->

## 4. 收尾

- [ ] 4.1 验证报告增补；验证：文档与证据一致 <!-- comet-task:0c3e4dd1-7b03-425e-92a2-0b7342ba4919 -->

```

## openspec/changes/ops-metrics-collection/.openspec.yaml

- Source: openspec/changes/ops-metrics-collection/.openspec.yaml
- Lines: 1-2
- SHA256: 8ba8273010ceb66cd0ab320b2f49de179fac6fd6f648317c2cc129442eea7dc0

```md
schema: spec-driven
created: 2026-10-09

```

## openspec/changes/ops-metrics-collection/specs/ops-metrics/spec.md

- Source: openspec/changes/ops-metrics-collection/specs/ops-metrics/spec.md
- Lines: 1-51
- SHA256: 81313b65c658fa3133009e7400f40ef1cfe370e475a82f90cca728d9bcd22642

```md
# 运营数据（发布事件、指标快照、只读归因）

## Purpose

统一管理各平台发布事件与其互动指标的时间序列快照，为运营复盘与内容策略校准提供唯一权威数据源。

## ADDED Requirements

### Requirement: 发布事件记录
发布成功后，系统 MUST 记录一条发布事件（平台、标题、内容类型、来源目录、发布链接、发布日、所属画像与选题方向）；同一来源目录 + 同一发布日重复记录 MUST 更新既有行而非插入新行。发布失败时 MUST 记录事件并注明原因，不静默丢弃。

#### Scenario: 发布成功后落库
- **GIVEN** 一篇草稿已在某平台发布成功
- **WHEN** 记录发布事件
- **THEN** 事件表出现一条记录，含平台/标题/链接/发布日/画像/选题方向

#### Scenario: 同日重复记录更新而非插入
- **GIVEN** 该来源目录与发布日的事件已存在
- **WHEN** 再次记录同一发布
- **THEN** 更新既有行（覆盖标题/链接），不新增行

### Requirement: 指标快照回收
系统 MUST 能按平台回收互动指标快照：公众号 MUST 通过已 vendor 的 wechat-mp-toolkit datacube 接口取数（用户增减、图文阅读、转发分享等）；小红书 MUST 通过自有创作者中心页面读取每篇笔记的指标列。快照 MUST 带采集时间戳与来源标记；采集失败 MUST 记录失败原因并保留历史值，不得用零值覆盖真实数据。

#### Scenario: 公众号 datacube 取数
- **GIVEN** 公众号有效凭据与日期区间
- **WHEN** 回收公众号指标
- **THEN** 快照记录用户增减与图文阅读/转发数据，附采集时间与来源（datacube）

#### Scenario: 小红书创作者中心取数
- **GIVEN** 小红书登录态有效
- **WHEN** 回收小红书指标
- **THEN** 快照记录每篇笔记的标题与页面指标列数值，附采集时间与来源（creator-center）

#### Scenario: 采集失败保留历史
- **GIVEN** 某次采集接口异常
- **WHEN** 写入快照
- **THEN** 记录失败原因，不将既有指标覆盖为零

### Requirement: 只读归因查询
归因查询 MUST 为只读操作（不修改事件与快照），结果由确定性脚本计算（趋势、内容生命周期判定如速爆型/稳增型/长尾型），系统 MUST NOT 让模型手工估算数值。

#### Scenario: 查询趋势与生命周期
- **GIVEN** 存在多次指标快照
- **WHEN** 执行归因查询
- **THEN** 输出按平台/画像的趋势与单篇内容生命周期判定，数据来自快照而非估算

#### Scenario: 查询不回写
- **GIVEN** 执行任意归因查询
- **WHEN** 查询完成
- **THEN** 事件与快照数据保持不变

```
