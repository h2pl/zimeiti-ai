---
comet_change: ops-metrics-pg
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-10-ops-metrics-pg
status: final
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
