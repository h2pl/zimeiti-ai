# harness-business-split 规格草案

## Purpose

agent harness 与业务代码分属两个包，依赖单向可由测试机械验证，业务对 harness
的调用只经显式注入点。

## ADDED Requirements

### Requirement: harness 包与业务包物理分离

系统 SHALL 包含与 `zimeiti_api` 平级的 `zimeiti_harness` 包，承载 agent 装配、
模型 fallback、exec 工具、记忆、用量、结构化 schema；业务域（content/automations/
platforms/operations）与 API 路由 MUST 留在 `zimeiti_api`。

#### Scenario: 包结构落位
- **WHEN** 检查仓库结构
- **THEN** `zimeiti_harness/` 含 runtime/memory/usage 与 contract 注入点，
  `zimeiti_api/runtime/` 不再存在，路由在 `zimeiti_api/chat_router.py` 等

### Requirement: harness 对业务域零 import 且有守卫

`zimeiti_harness` 源码 MUST NOT import 业务域（content/automations/platforms/
operations/governance 及其符号）；允许 import 共享 infra `zimeiti_api.core`。
确定性测试 SHALL 扫描 harness 源码并断言零违规，随 make check 运行。

#### Scenario: 守卫测试拦截回潮
- **WHEN** 任何人向 `zimeiti_harness/` 内的文件加入 `from zimeiti_api.content...`
- **THEN** `make check` 的分层守卫测试失败并指出违规文件与行

### Requirement: 业务对 harness 只经注入点

业务模块 MUST NOT 硬 import harness 的 agent 入口；需要 agent 能力的模块
（如 automations scheduler）SHALL 通过组装层注入的 setter 获得入口
（对齐 personas 的 set_enhance_runtime 范式）。

#### Scenario: scheduler 经注入获得 ask_sync
- **WHEN** 定时任务执行 prompt 类型任务
- **THEN** ask_sync 来自组装层注入的 setter，scheduler 源码无
  `from ..runtime.../from zimeiti_harness...` 的 agent 入口 import

### Requirement: 行为零变化

本次为纯结构重构：全量测试、E2E、行为探针结果 MUST 与重构前一致
（229 单测 / E2E 63 项 / 探针 PASS）。
