# Comet Design Handoff

- Change: phase1-easel-api-copy
- Phase: design
- Mode: compact
- Context hash: 94f75c125131a00d52931bbce3ace75ca0c79de357c3dd7c75252d35d34208e7

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/phase1-easel-api-copy/proposal.md

- Source: docs/openspec/changes/phase1-easel-api-copy/proposal.md
- Lines: 1-28
- SHA256: d794a92ceb8d2513702a8243a82cf47f15a07c5e209f8087d91619deb03560f2

```md
## Why

全新项目（起点分支 `zimeiti-init` 无代码）。按 `docs/prd/zimeiti-ai-prd.md`：阶段一先复制实现 Easel，且后端最终要与 OpenClaw 解耦、改用 deepagents 实现。

本变更是阶段一的后半部：**把 Easel 后端复制过来并跑起来**，同时登记其中依赖 OpenClaw 的模块，作为后续"去 OpenClaw、改用 deepagents"变更的输入。前端复制由独立变更 `phase1-easel-web-copy` 承担。

## What Changes

- 新建 `apps/api`：整份复制 Easel 后端 `easel/` 包与 `web/app.py`
- 复制后端依赖配置（`pyproject.toml` / `requirements`）
- 安装依赖并启动服务，确认 `/api/status` 有响应
- 登记依赖 OpenClaw 的模块清单（`openclaw_cmd.py`、`openclaw_workspace.py`、`gateway_endpoint.py`、`gateway_questions.py`、`local_agents.py`、`commands/*` 等）

## Capabilities

### New Capabilities

- `easel-api-copy`: 以 Easel 后端源码为起点的 API 工程——源码复制完整、依赖就绪、服务可启动，并输出 OpenClaw 依赖清单

### Modified Capabilities

（无。全新项目，无既有能力规格。）

## Impact

- 新增 `apps/api/`（`easel/`、`app.py`、依赖配置）
- 本地后端启动方式改为 `apps/api` 下的 API 服务
- 本变更不移除 OpenClaw 依赖，只登记；解耦归后续变更

```

## docs/openspec/changes/phase1-easel-api-copy/design.md

- Source: docs/openspec/changes/phase1-easel-api-copy/design.md
- Lines: 1-70
- SHA256: c93c6285822b0da89c5f6a0740a77fc80a49e42f33056ecc878a6dec56e40eb5

```md
---
comet_change: phase1-easel-api-copy
role: technical-design
canonical_spec: openspec
---
## Context

全新项目，起点分支 `zimeiti-init` 无代码。本变更复制 Easel 后端；前端复制由 `phase1-easel-web-copy` 承担。

复制源：`E:\Projects\Easel\easel/`（Python 包）与 `E:\Projects\Easel\web/app.py`（FastAPI 应用，4419 行）。

已知事实：

- OpenClaw 依赖集中在 `easel/openclaw_cmd.py`、`openclaw_workspace.py`、`gateway_endpoint.py`、`gateway_questions.py`、`local_agents.py`、`commands/*`
- 本环境未安装 OpenClaw 可执行文件（`Easel/openclaw/` 只有 config 与 sync.sh）
- zimeiti 旧后端已是 deepagents 运行时，后续解耦以此为替代实现

## Goals / Non-Goals

**Goals:**

- 复制 Easel 后端源码与依赖配置到 `apps/api`
- 装依赖、启动服务、`/api/status` 有响应
- 输出 OpenClaw 依赖清单

**Non-Goals:**

- 不在本变更移除或替换 OpenClaw 依赖
- 不复制/改造前端
- 不实现 xiaobei 能力

## Decisions

### 决策 1：整份复制，先跑起来再解耦

- **选择**：`easel/` 与 `app.py` 整份复制，本变更只求服务能启动
- **理由**：先拿到与 Easel 一致的后端基线，解耦时有明确对照
- **备选**：复制同时替换 OpenClaw → 改动与复制混杂，出问题难定位，否决

### 决策 2：OpenClaw 缺失先登记不处理

- **选择**：登记依赖清单，服务能起来即可
- **理由**：解耦是后续变更的工作；当前环境无 OpenClaw，强行处理会阻塞跑通
- **备选**：本变更即替换 → 超出"复制并跑起来"范围，否决

### 决策 3：依赖配置随源码复制

- **选择**：复制 Easel 的 `pyproject.toml` / requirements 并对齐
- **理由**：Easel 代码假设其依赖版本，自造清单易引入差异
- **备选**：手写依赖清单 → 易漏依赖，否决

## Risks / Trade-offs

- **[风险] OpenClaw 缺失导致依赖它的接口不可用** → 缓解：本变更只要求服务可启动、`/api/status` 有响应
- **[风险] Python 版本/平台差异导致依赖安装失败** → 缓解：对齐 Easel 版本，失败即记录
- **[风险] 端口占用** → 缓解：启动时指定空闲端口

## Migration Plan

1. 复制 `easel/` → `apps/api/easel/`，`web/app.py` → `apps/api/app.py`
2. 复制依赖配置并对齐
3. 安装依赖（使用项目既有虚拟环境或新建）
4. 启动服务，验证 `/api/status` 有响应
5. 输出 OpenClaw 依赖模块清单

**回滚**：分支隔离，丢弃分支即回到 `zimeiti-init`。

## Open Questions

- 无（本变更只做复制与跑通）

```

## docs/openspec/changes/phase1-easel-api-copy/tasks.md

- Source: docs/openspec/changes/phase1-easel-api-copy/tasks.md
- Lines: 1-16
- SHA256: 2ba241a814dfee03f5b255838520a2921d52814793899d8180b60b78b0239108

```md
## 1. 复制后端源码与配置

- [ ] 1.1 复制 Easel `easel/` → `apps/api/easel/`，`web/app.py` → `apps/api/app.py`
- [ ] 1.2 复制依赖配置（pyproject.toml / requirements）→ `apps/api`
- [ ] 1.3 验证：文件与 Easel 逐行一致，包目录无遗漏

## 2. 安装依赖并启动服务

- [ ] 2.1 准备 Python 环境并安装依赖
- [ ] 2.2 启动服务（指定空闲端口）
- [ ] 2.3 验证：`/api/status` 返回响应，服务无致命启动报错

## 3. 登记 OpenClaw 依赖清单

- [ ] 3.1 梳理后端中依赖 OpenClaw 的模块并写入变更记录
- [ ] 3.2 验证：清单覆盖所有 import openclaw 或调用 OpenClaw 命令的文件

```

## docs/openspec/changes/phase1-easel-api-copy/.openspec.yaml

- Source: docs/openspec/changes/phase1-easel-api-copy/.openspec.yaml
- Lines: 1-2
- SHA256: f2045744e0afbc626aea7f3e957df5a86f90906c2a017bb3f74a29245fad9d1e

```md
schema: spec-driven
created: 2026-10-13

```

## docs/openspec/changes/phase1-easel-api-copy/specs/easel-api-copy/spec.md

- Source: docs/openspec/changes/phase1-easel-api-copy/specs/easel-api-copy/spec.md
- Lines: 1-26
- SHA256: fed4caca35073e93d569a007e15f65189119d6cb34bbdad974e4a0692e8ee552

```md
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

```
