# usage-pricing Specification

## Purpose
让「花了多少钱」可回答（有单价数据时），让单 key 限流不再直接烧备用模型（key 轮换先于模型切换）。

## Requirements

### Requirement: 用量金额折算

用量统计对**有单价数据**的模型按 token 折算 USD 金额；**无单价数据**的模型金额为 null 并如实标注，不编造。

#### Scenario: 已知模型折算
- **WHEN** 用量统计包含单价表内模型（如 deepseek-chat）的记录
- **THEN** 该行与总计包含 `cost_usd` 字段，按「输入/输出分别计价」计算

#### Scenario: 未知模型不编造
- **WHEN** 用量记录的模型不在单价表（或模型名为空）
- **THEN** 该行 `cost_usd` 为 null；总计为「已知部分之和」，界面标注「部分未计价」

### Requirement: 多 key 轮换先于模型 fallback

配置 `ZIMEITI_API_KEYS`（逗号分隔）时，模型链前置「主模型 × 各 key」节点；单 key 限流/连接失败先换 key，key 用尽才切备用模型；切换日志区分换 key 与换模型。

#### Scenario: 限流先换 key
- **WHEN** 主模型在 key1 上遇 429/连接错误且配置了多 key
- **THEN** 先以 key2 重试同一模型；全部 key 失败后才进入备用模型链

#### Scenario: 未配置多 key 行为不变
- **WHEN** 未设置 `ZIMEITI_API_KEYS`
- **THEN** 行为与之前完全一致（单 key → 备用模型链）
