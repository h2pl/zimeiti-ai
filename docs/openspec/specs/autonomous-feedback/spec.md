# autonomous-feedback Specification

## Purpose
把已发布事实汇总成校准信号并注入发现层，让运营链路具备「上一轮影响下一轮」的
闭环；数据缺失时如实降级，绝不虚构表现。

## Requirements

### Requirement: 发布事实汇总

系统 SHALL 汇总既有发布事实（`outputs/_analytics/<platform>/<date>.json`），
MUST 按平台与时间窗聚合，并 MUST 在源缺失或不可解析时返回空结果（不报错、不虚构）。

#### Scenario: 有发布事实
- **WHEN** `outputs/_analytics/wechat/2026-10-18.json` 存在且含两条记录
- **THEN** 汇总结果含平台 wechat、条数 2、标题/时间等事实字段

#### Scenario: 无发布事实
- **WHEN** `outputs/_analytics/` 不存在或为空
- **THEN** 汇总返回空列表，校准信号如实说明「暂无发布记录」，不编造任何表现数据

### Requirement: 校准信号注入发现层

`runner` 在执行 **discover 步**时 SHALL 注入校准信号到该步 prompt；其余步骤
MUST NOT 受此影响。校准信号 MUST 只陈述事实与缺口提示，不得包含虚构的表现数值。

#### Scenario: 注入可观测
- **WHEN** 流程含 discover 步且存在发布事实
- **THEN** discover 步的入参 prompt 含校准段（含平台与条数事实），且 produce 步的
  prompt 不含该段

#### Scenario: 无数据时降级
- **WHEN** 无发布事实
- **THEN** discover 步 prompt 的校准段如实写「暂无发布记录」，流程正常执行

### Requirement: 校准结论归档

系统 SHALL 把每次生成的校准信号归档到 `outputs/_feedback/<date>.md`，并 SHALL
通过 `GET /api/feedback` 暴露最近一次校准信号。

#### Scenario: 归档与查询
- **WHEN** 生成校准信号后
- **THEN** `outputs/_feedback/<date>.md` 存在且 `GET /api/feedback` 返回其内容摘要
