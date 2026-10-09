# 验证报告（Verify Report）——变更 ops-metrics-pg

- 日期：2026-10-09
- 分支：comet/ops-metrics-pg
- 范围：运营数据存储后端从 SQLite 迁回项目 Postgres

## 结论

**通过（Go）**——双数据源消除，PG 落库与后台数值一致：

- gzh：datacube 真实返回（新增 1 / 取消 0）
- xhs：创作者中心看板（关注 6 / 粉丝 212 / 获赞与收藏 5281）
- 快照写入 PG `metric_snapshots`（source=datacube / creator-center）
- 门禁：make check 80 passed，覆盖率 ≥80%

## 校验记录

| 项 | 结果 | 证据 |
|---|---|---|
| 存储后端 | 三表建于项目 Postgres（SERIAL 主键、ON CONFLICT upsert） | `information_schema.tables` 查询 + 单测 |
| 行为不变 | 事件 upsert / 快照 / 失败留痕 / 只读归因全部用例复用通过 | tests/test_ops_metrics.py（80 passed） |
| 一次性迁移 | 旧 SQLite → PG 行一致 | TestSqliteMigration |
| 真账号取数 | 双平台 ok=true，数值与后台一致 | `ops_metrics pull` 输出 + PG 查询 |

## 选型修正记录

ops-metrics-collection 引入 SQLite 属选型失误：项目已运行 Postgres（langgraph
AsyncPostgresSaver 依赖它、psycopg 已是依赖），且 PRD 商业化路径为订阅 SaaS（多租户）、
ROADMAP 明确计量埋点——指标必须落在 PG。根因是照抄 xiaobei `published-track` 时
连其**基础设施选型**一起搬了（xiaobei 生态无 PG）；本次只保留其**逻辑**
（upsert 去重键、失败留痕、关联维度），存储统一到 PG。

## 遗留

1. 连接为短连接（每次操作新建），量产后可考虑连接池
2. 测试使用独立 schema `zimeiti_metrics_test`，需在 CI 具备建 schema 权限
