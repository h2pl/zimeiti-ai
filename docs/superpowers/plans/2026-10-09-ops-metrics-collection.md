---
change: ops-metrics-collection
design-doc: openspec/changes/ops-metrics-collection/design.md
base-ref: 1cee0e6fbb6ed7a5508fda933906f9494a0f7b57
archived-with: 2026-10-09-ops-metrics-collection
---

<!-- comet-task-authority: openspec/changes/ops-metrics-collection/tasks.md -->

# 实施计划：ops-metrics-collection

运营数据闭环：发布事件记录 + 指标快照回收（gzh datacube / xhs 创作者中心）+ 只读归因查询。
设计合成自 xiaobei published-track（SQLite/upsert/关联校准）与 Easel 数据三层
（事件与快照分离、消费只读、确定性脚本聚合）。

## Phase A 数据层（任务 1.1-1.3）

SQLite 三表与 upsert 去重 → gzh datacube 取数 → xhs 创作者中心取数。
验收：单测覆盖幂等 upsert、失败保留历史、列解析。

## Phase B 只读消费（任务 2.1）

趋势与内容生命周期判定（确定性规则），全程只读不回写。
验收：单测断言结果且不回写。

## Phase C 真账号走查与收尾（任务 3.1 / 4.1）

双平台真实取数一次并与后台人工比对 → 验证报告增补。

## 任务引用（canonical refs）

<!-- comet-task-ref:8d8c204c-c3b9-4bc2-8fe5-dc688914368f -->
<!-- comet-task-ref:395260eb-f627-4aad-8eee-6120a3a7ae12 -->
<!-- comet-task-ref:75778886-c690-4d6f-92c2-1f9046edacde -->
<!-- comet-task-ref:eee6978a-b4aa-4895-bd7c-1433e6896c4d -->
<!-- comet-task-ref:563f8837-3e25-4909-9ddf-7c12db00f8f4 -->
<!-- comet-task-ref:0c3e4dd1-7b03-425e-92a2-0b7342ba4919 -->
