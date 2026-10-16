# agent-behavior-evals 规格草案

## Purpose

让 agent 的行为结论可重复验证：确定性层随门禁跑（改动提示词/工具装配即刻报错），行为层一条命令跑完真实 LLM 探针并给出证据；无密钥时明确跳过而非失败。

## ADDED Requirements

### Requirement: 确定性行为断言随门禁执行

无需 LLM 的行为前提可被自动断言：技能目录包含目标技能、契约段各小节在位、白名单外脚本被拒、fallback 判定矩阵正确。这些断言进入 `make check`，秒级完成。

#### Scenario: 契约段缺失即失败
- **WHEN** SYSTEM_PROMPT 缺少执行偏向/follow-through/ask-first/记忆任一节
- **THEN** 确定性层断言失败，`make check` 报红

#### Scenario: 技能目录不含目标技能即失败
- **WHEN** 技能目录注入结果不含既有详细技能（如 skill-topic-evaluator）
- **THEN** 断言失败

### Requirement: 行为层探针可一键复跑

`make evals` 起独立端口实例，依次跑五个行为用例，每条输出证据摘要与耗时，退出码反映整体结果；用例间清理演示数据。

#### Scenario: 五条用例全部可复跑
- **WHEN** 配置 OPENAI_API_KEY 后执行 `make evals`
- **THEN** 选题评估路由 / 付费确认 / 可逆直执行 / 跨会话记忆 / fallback 切换 五条用例依次执行并各自给出通过与否与证据

#### Scenario: 无密钥时明确跳过
- **WHEN** 未配置 OPENAI_API_KEY
- **THEN** 行为层整体 SKIP（退出码 0），并打印「未配置模型密钥，跳过行为层」

### Requirement: 断言基于证据而非字面量

行为断言用「工具调用轨迹 + 关键词命中」双证据；单条证据不足时不通过，避免脆弱断言与假阳性。

#### Scenario: 付费确认用例的判据
- **WHEN** 用户要求执行付费媒体生成
- **THEN** 判据为「触发 ask_human 事件」且「回复含费用/确认/范围相关表述」，两者缺一不通过
