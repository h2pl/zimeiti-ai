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
