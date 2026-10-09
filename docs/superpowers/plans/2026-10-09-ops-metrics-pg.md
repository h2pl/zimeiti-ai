---
change: ops-metrics-pg
design-doc: openspec/changes/ops-metrics-pg/design.md
base-ref: 9e5f3211e1b5f1b2b8f3a1c6f5c1a2d3e4f5a6b7
archived-with: 2026-10-10-ops-metrics-pg
---

<!-- comet-task-authority: openspec/changes/ops-metrics-pg/tasks.md -->

# 实施计划：ops-metrics-pg

运营数据存储后端从 SQLite 迁回项目 Postgres（消除第二套 SQL 引擎），
表结构与业务逻辑不变。

## Phase A 存储层（任务 1.1-1.2）

psycopg 连接 + SERIAL/%s 改写 + setup() 幂等建表 → 保留一次性 SQLite 搬运子命令。
验收：现有全部数据层单测复用通过。

## Phase B 真账号复跑与收尾（任务 2.1 / 3.1）

双平台真实取数并确认 PG 落库一致 → 验证报告增补。

## 任务引用（canonical refs）

<!-- comet-task-ref:94653e9b-30d5-4977-a838-158a3ff70f6c -->
<!-- comet-task-ref:c31c3aa7-f5f7-4f01-a80f-e2e9b9ff9845 -->
<!-- comet-task-ref:b51042ce-5691-4c3c-b955-69d9223b24bd -->
<!-- comet-task-ref:f5c01484-7cdc-4326-8643-954864e736d9 -->
