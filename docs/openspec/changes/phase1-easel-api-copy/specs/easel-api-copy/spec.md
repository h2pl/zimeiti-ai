## Purpose

定义"复制 Easel 后端源码建立本项目 API 工程并跑起来"的验收标准：源码完整、依赖就绪、服务可启动，并输出后续解耦所需的 OpenClaw 依赖清单。

## ADDED Requirements

### Requirement: 后端源码复制完整且保真

#### Scenario: 文件比对

- **WHEN** 对比 `apps/api` 与 Easel 后端（`easel/`、`web/app.py`）的同名文件
- **THEN** 内容逐行一致，包目录无遗漏

### Requirement: 服务可启动

#### Scenario: 健康检查

- **WHEN** 在 `apps/api` 安装依赖并启动服务
- **THEN** `/api/status` 返回响应；网关未连接属于正常，只要服务本身起得来、接口有响应

### Requirement: OpenClaw 依赖清单登记

#### Scenario: 清单产出

- **WHEN** 复制完成后梳理后端依赖
- **THEN** 列出所有依赖 OpenClaw 的模块文件（已知包含 `openclaw_cmd.py`、`openclaw_workspace.py`、`gateway_endpoint.py`、`gateway_questions.py`、`local_agents.py`、`commands/*`），作为后续 deepagents 解耦变更的输入
