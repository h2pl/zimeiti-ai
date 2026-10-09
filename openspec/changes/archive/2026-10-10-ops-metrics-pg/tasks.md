# Tasks

## 1. 存储层迁移

- [x] 1.1 MetricsDB 改 psycopg：DATABASE_URL 连接 + SERIAL 主键 + %s 占位符 + setup() 幂等建表；验证：单测覆盖 upsert/快照/失败留痕/只读归因全部复用现有用例 <!-- comet-task:94653e9b-30d5-4977-a838-158a3ff70f6c -->
- [x] 1.2 保留一次性 migrate-from-sqlite 子命令（旧 SQLite 文件搬运到 PG）；验证：单测用临时 SQLite 文件搬运后行一致 <!-- comet-task:c31c3aa7-f5f7-4f01-a80f-e2e9b9ff9845 -->

## 2. 真账号复跑

- [x] 2.1 双平台真实取数一次，确认 PG 落库与后台数值一致；验证：PG 表行数 + 数值一致 <!-- comet-task:b51042ce-5691-4c3c-b955-69d9223b24bd -->

## 3. 收尾

- [x] 3.1 验证报告增补；验证：文档与证据一致 <!-- comet-task:f5c01484-7cdc-4326-8643-954864e736d9 -->
