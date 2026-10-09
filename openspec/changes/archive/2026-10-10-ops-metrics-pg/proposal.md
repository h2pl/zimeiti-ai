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
