# autonomous-observability Specification

## Purpose
让自主运营的状态在页面上可见：流程、执行记录、待人工确认项、熔断态、预算用量
一处可查，用户能放心把运营交给 agent。

## Requirements

### Requirement: 执行记录可查

系统 SHALL 提供 `GET /api/flows/runs`（可按 flow_id 过滤），MUST 返回每次执行的
状态、耗时与步骤级明细（步骤名、状态、耗时、错误）。

#### Scenario: 查询某流程的执行记录
- **WHEN** 调用 `GET /api/flows/runs?flow_id=<id>`
- **THEN** 返回该流程最近若干次执行，每次含步骤明细（含 blocked/failed 的步骤）

### Requirement: 自主运营页面

前端 SHALL 提供「自主运营」页面，MUST 展示流程列表与最近执行记录，并 MUST 展示
待确认（blocked）清单、熔断提示与当日预算用量；页面样式 MUST 沿用既有设计体系
（page-scroll / page-title / panel / field / btn / badge / card）。

#### Scenario: 看板可见四要素
- **WHEN** 用户打开「自主运营」页
- **THEN** 可见流程列表、执行记录、待确认项（或「无待确认项」）、预算用量
  （无单价时如实说明未折算）

#### Scenario: 新建流程勾选步骤
- **WHEN** 用户新建流程并勾选 discover/plan 两步、填名称与调度后保存
- **THEN** 流程出现在列表且步骤显示为所选子集

### Requirement: E2E 与文档

E2E SHALL 新增场景覆盖该页（记为 zimeiti 独有，easel 侧按预期差异 NOTE）；
README SHALL 新增「自主运营」章节说明编排/回流/护栏与看板。

#### Scenario: E2E 覆盖
- **WHEN** 运行全量 E2E
- **THEN** 场景数由 12 增至 13，全部通过且双端差异为 0（预期差异记 NOTE）
