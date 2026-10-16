# agent-subagents-output 规格草案

## Purpose

让子代理有角色边界与成本分层，让结构化产出有 schema 约束：探索类子任务可用便宜模型且只读，写作子代理限定产出范围；结构化请求可按 schema 产出（首个场景：选题评估评分表）。

## ADDED Requirements

### Requirement: 专属子代理可按角色派生

主 agent 可派生「只读探索」与「写作」两种角色子代理；只读子代理不得具备写文件工具，写作子代理不得具备提问与脚本执行工具；子代理模型可独立配置（缺省同主模型）。

#### Scenario: 探索类子任务用只读子代理
- **WHEN** 主 agent 需要大范围检索技能库/内容库/历史产物
- **THEN** 派 `research` 子代理完成；该子代理工具面只含只读工具，回报事实与路径
- **THEN** 若配置了 `ZIMEITI_SUBAGENT_MODEL`，该子代理用便宜模型而非主模型

#### Scenario: 子代理不得越权
- **WHEN** 子代理被派生
- **THEN** 它拿不到 ask_human（不打断用户）与 exec_script（不跑脚本）；只读子代理拿不到写工具

#### Scenario: 可关闭
- **WHEN** 设置 `ZIMEITI_SUBAGENT_ENABLED=false`
- **THEN** 退回 deepagents 默认通用子代理行为

### Requirement: 结构化输出按 schema 产出

结构化请求可指定 schema，agent 按 schema 产出结构化结果；首个落地场景为选题评估评分表（维度分+综合结论+建议）。

#### Scenario: 选题评估结构化产出
- **WHEN** 以结构化方式请求选题评估
- **THEN** 返回符合 schema 的结果（各维度分数、综合结论、建议要点），字段齐全且类型正确

#### Scenario: 不影响普通对话
- **WHEN** 普通对话未指定 schema
- **THEN** 行为与之前一致（不强制结构化）
