# cli-entry-point 规格草案

## Purpose

提供一个不开浏览器就能用的命令行入口：对话、运营流程管理、执行记录、用量。

## ADDED Requirements

### Requirement: 对话命令

CLI SHALL 提供 `zimeiti chat "消息"`，按服务端 SSE 契约流式输出回复
（token 增量、activity 进度、error 可读错误），MUST NOT 在本地持有任何模型凭据。

#### Scenario: 流式对话
- **WHEN** 服务可用且用户执行 `zimeiti chat "你好"`
- **THEN** 终端逐段打印回复内容；结束后显示用量摘要（token 数）

#### Scenario: 服务不可达
- **WHEN** 后端未启动（连接被拒绝）
- **THEN** 输出可行动错误（提示 `make api` 启动服务或检查 `--base`），退出码非 0

### Requirement: 运营流程命令

CLI SHALL 提供 `flows`（列表）、`flows new`（新建，参数含名称/步骤子集/调度）、
`flows run`（立即执行）、`runs`（执行记录含步骤明细）、`usage`（用量）子命令，
全部 MUST 基于既有 HTTP API，且 SHALL 在输出中如实呈现服务端状态
（如 blocked/failed 步骤、未折算金额）。

#### Scenario: 新建流程
- **WHEN** 执行 `zimeiti flows new --name 每日选题 --steps discover,plan`
- **THEN** 流程创建成功并回显流程 id；`zimeiti flows` 能看到该流程及步骤徽标

#### Scenario: 执行记录逐步可见
- **WHEN** 执行 `zimeiti runs`
- **THEN** 每次执行显示状态/耗时，并逐步列出步骤状态（完成/待确认/失败）

#### Scenario: 立即执行须明示成本
- **WHEN** 用户执行 `zimeiti flows run <id>`
- **THEN** 命令帮助文本中 MUST 说明该操作会真实消耗模型额度

### Requirement: 安装与可发现性

CLI SHALL 通过 console script 安装为 `zimeiti` 命令，SHALL 支持
`--help` 列出全部子命令，MUST 不引入第三方运行时依赖（stdlib 实现）。

#### Scenario: 安装后可用
- **WHEN** 安装项目（`make install` / `uv sync`）后执行 `zimeiti --help`
- **THEN** 列出 chat/flows/runs/usage 子命令及说明
