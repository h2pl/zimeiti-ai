# agent-shell-exec Specification

## Purpose
让 agent 能安全地执行已注册的脚本（质检/渲染等收尾能力），补齐「自动化最后一公里」；安全边界为静态白名单——agent 无法执行注册表之外的任何命令。

## Requirements

### Requirement: 白名单脚本执行

系统提供 ExecTool 工具，agent 可执行注册表中的脚本；注册表外的任何调用被拒绝并返回明确错误。

#### Scenario: 执行注册脚本
- **WHEN** agent 调用 ExecTool 执行注册表中的脚本（如 ai_score.py）并传合法参数
- **THEN** 脚本在数据根目录执行，agent 收到其 stdout/stderr（超长时截断保留尾部）
- **THEN** 退出码非零时错误信息中包含退出码与输出

#### Scenario: 拒绝未注册脚本
- **WHEN** agent 尝试执行注册表之外的命令或脚本
- **THEN** 调用被拒绝，错误信息说明白名单机制并列出可用脚本

### Requirement: 参数与路径安全

ExecTool 的参数经白名单校验：仅接受脚本声明的参数形态；含路径穿越（`..`）、绝对路径、命令替换字符（`$`、反引号、管道）的参数被拒绝。

#### Scenario: 路径注入被拒
- **WHEN** 参数值包含 `../`、绝对路径或命令替换字符
- **THEN** 调用被拒绝，不产生任何进程创建

### Requirement: 执行资源约束

每次执行有超时上限与输出上限；执行以数据根为工作目录、UTF-8 解码输出；超时进程被终止并返回超时错误。

#### Scenario: 超时被终止
- **WHEN** 注册脚本运行超过超时上限
- **THEN** 进程被终止，agent 收到明确的超时错误
