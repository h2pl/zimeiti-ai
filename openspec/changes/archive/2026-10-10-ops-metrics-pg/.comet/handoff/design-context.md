# Comet Design Handoff

- Change: ops-metrics-pg
- Phase: design
- Mode: compact
- Context hash: de22a3a120b1dd58766a5e9643d9fe3d846cc47d2e10cb9278a220c31198b5ed

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/ops-metrics-pg/proposal.md

- Source: openspec/changes/ops-metrics-pg/proposal.md
- Lines: 1-29
- SHA256: 97d1263d6eb2346c1545c643affa83e5b49d088e0960fbc6776a31263ff715df

```md
# Why

ops-metrics-collection（已归档）引入了 SQLite 作为运营数据表存储，形成第二套 SQL 引擎。项目已运行 Postgres（`DATABASE_URL`，langgraph `AsyncPostgresSaver` 依赖它，psycopg 已是依赖），且 PRD 商业化路径为订阅 SaaS（多租户）、ROADMAP 明确「多租户与计费（架构预留计量埋点）」——运营指标最终必须落在 PG 上以支持租户隔离与计量查询。

选型失误根因：照抄 xiaobei `published-track` 时连其基础设施选型一起搬了（xiaobei 运行在 OpenClaw + 文件/SQLite 生态，本无 PG），违反「复用逻辑而非搬迁技术栈」的本意。本变更把运营数据迁回 PG，消除双数据源。

# What Changes

- `ops_metrics.py` 数据层从 sqlite3 改为 psycopg（PG），SQL 语义保持一致（upsert 去重、快照、失败留痕、只读归因）
- 表结构迁入 PG：`publish_events` / `metric_snapshots` / `collection_errors`（`SERIAL` 主键、`ON CONFLICT` upsert 原样保留）
- 连接串复用 `config.DATABASE_URL`；`setup()` 幂等建表（对齐 `checkpoints.py` 的 setup 惯例）
- 已有 SQLite 数据（若有）不迁移：当前无生产数据，首次建表即可；提供一次性 `migrate-from-sqlite` 子命令以便需要时搬运

# Capabilities

## Modified Capabilities

- `ops-metrics`：存储后端改为 Postgres（行为与场景不变，仅存储实现变更）

## Added Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/ops_metrics.py`（存储层替换）
- 依赖：psycopg[binary]（已在依赖清单，供 checkpointer 使用）
- 移除 sqlite3 依赖使用；`data/metrics/published.db` 不再生成
- 前置：Postgres 需运行（与 checkpointer 一致，`make test` 已内置预检）

```

## openspec/changes/ops-metrics-pg/design.md

- Source: openspec/changes/ops-metrics-pg/design.md
- Lines: 1-47
- SHA256: b36ff7e98e93b84ec2739a1fa05ecff708d901f980d6f3833460fb48d9efa842

```md
---
comet_change: ops-metrics-pg
role: technical-design
canonical_spec: openspec
status: draft
---

# Design：ops-metrics-pg

## D0 选型修正：单数据源

运营数据迁回项目 Postgres，消除 SQLite 第二套引擎。依据：

- PG 已是运行必需（`DATABASE_URL`，langgraph `AsyncPostgresSaver`），`psycopg[binary]` 已在依赖清单
- PRD 商业化路径为订阅 SaaS（多租户），ROADMAP 明确「多租户与计费（架构预留计量埋点）」——指标必须落在可租户隔离、可计量查询的库上
- 原 SQLite 选型源自照抄 xiaobei `published-track` 的**基础设施**（其生态无 PG），属照抄场景不匹配；本次只保留其**逻辑**（upsert 去重键、失败留痕、关联维度）

## D1 数据模型（PG，语义不变）

沿用 ops-metrics-collection 的三表与窄表快照设计，仅改类型与占位符：

| 变更点 | SQLite → PG |
|---|---|
| 主键 | `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY` |
| 占位符 | `?` → `%s` |
| 建表 | `CREATE TABLE IF NOT EXISTS`（PG 支持，保持不变） |
| upsert | `ON CONFLICT(...) DO UPDATE SET`（PG 原生，保持不变） |
| 连接 | `sqlite3.connect(path)` → `psycopg.connect(DATABASE_URL)` |

表名与字段完全不变，查询/归因逻辑零改动。

## D2 连接与建表

- 连接串复用 `zimeiti_api.config.DATABASE_URL`
- `MetricsDB.setup()` 幂等建表，与 `checkpoints.py` 的 `saver.setup()` 惯例一致（首次调用建表，重复调用无副作用）
- 连接生命周期：**每次操作短连接**（`with psycopg.connect(...) as conn`），与当前 SQLite 每次开连接的用法对齐，避免长连接管理；后续如需连接池再优化

## D3 迁移与兼容

- 当前无生产数据，`setup()` 建表即可；保留一次性 `migrate-from-sqlite --path <db>` 子命令（从旧 SQLite 文件搬运到 PG），便于需要时无损迁移
- 数据目录 `data/metrics/` 不再生成 `published.db`

## D4 测试策略

- 单测用 PG（conftest 已有 Postgres 预检），表前缀隔离（测试库同名表，用例结束清理自己的数据行）
- 解析纯函数（datacube / xhs 看板 / 生命周期判定）测试保持不变
- 真账号取数复跑一次，验证 PG 落库与数值一致

```

## openspec/changes/ops-metrics-pg/tasks.md

- Source: openspec/changes/ops-metrics-pg/tasks.md
- Lines: 1-14
- SHA256: 44ffa7907f62f11afbfec6f8aa0c32599bfec4e7ace705c2e497bfe81ce20408

```md
# Tasks

## 1. 存储层迁移

- [ ] 1.1 MetricsDB 改 psycopg：DATABASE_URL 连接 + SERIAL 主键 + %s 占位符 + setup() 幂等建表；验证：单测覆盖 upsert/快照/失败留痕/只读归因全部复用现有用例
- [ ] 1.2 保留一次性 migrate-from-sqlite 子命令（旧 SQLite 文件搬运到 PG）；验证：单测用临时 SQLite 文件搬运后行一致

## 2. 真账号复跑

- [ ] 2.1 双平台真实取数一次，确认 PG 落库与后台数值一致；验证：PG 表行数 + 数值一致

## 3. 收尾

- [ ] 3.1 验证报告增补；验证：文档与证据一致

```

## openspec/changes/ops-metrics-pg/.openspec.yaml

- Source: openspec/changes/ops-metrics-pg/.openspec.yaml
- Lines: 1-2
- SHA256: 8ba8273010ceb66cd0ab320b2f49de179fac6fd6f648317c2cc129442eea7dc0

```md
schema: spec-driven
created: 2026-10-09

```

## openspec/changes/ops-metrics-pg/specs/ops-metrics/spec.md

- Source: openspec/changes/ops-metrics-pg/specs/ops-metrics/spec.md
- Lines: 1-52
- SHA256: bc4bd42952428eb87a11fe7348befcbb9efa6f8ebe1ca90a53eb368d00c3c850

```md
# 运营数据（存储后端变更）

## MODIFIED Requirements

### Requirement: 指标快照回收
系统 MUST 能按平台回收互动指标快照：公众号 MUST 通过已 vendor 的 wechat-mp-toolkit datacube 接口取数（用户增减、图文阅读、转发分享等）；小红书 MUST 通过自有创作者中心页面读取账号级指标。快照 MUST 带采集时间戳与来源标记；采集失败 MUST 记录失败原因并保留历史值，不得用零值覆盖真实数据。

#### Scenario: 快照写入项目数据库
- **GIVEN** 一次取数完成
- **WHEN** 写入快照
- **THEN** 数据写入项目 Postgres（`DATABASE_URL`）的 metric_snapshots 表，不引入第二套 SQL 引擎

#### Scenario: 公众号 datacube 取数
- **GIVEN** 公众号有效凭据与日期区间
- **WHEN** 回收公众号指标
- **THEN** 快照记录用户增减与图文阅读/转发数据，附采集时间与来源（datacube）

#### Scenario: 小红书创作者中心取数
- **GIVEN** 小红书登录态有效
- **WHEN** 回收小红书指标
- **THEN** 快照记录账号级指标（关注数/粉丝数/获赞与收藏/曝光数/观看数/点赞数等），附采集时间与来源（creator-center）

#### Scenario: 采集失败保留历史
- **GIVEN** 某次采集接口异常
- **WHEN** 写入快照
- **THEN** 记录失败原因，不将既有指标覆盖为零

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
