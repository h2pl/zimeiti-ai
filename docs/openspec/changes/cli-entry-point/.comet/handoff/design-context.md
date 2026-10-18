# Comet Design Handoff

- Change: cli-entry-point
- Phase: design
- Mode: compact
- Context hash: d45a0b1720ecf328347a26d8def28d8ae6c3ed008410a73c1b2f79ddb00b63d9

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/cli-entry-point/proposal.md

- Source: docs/openspec/changes/cli-entry-point/proposal.md
- Lines: 1-51
- SHA256: 82e63f9cd8d838c8ed3d1287aaf2dd5308d6c380c2ec60b19e147bca78688e3b

```md
---
comet_change: cli-entry-point
---

# cli-entry-point：命令行入口（chat / flows / runs / usage）

## Why

现状取证（grep 级）：**面向人的交互入口只有 Web UI**（`apps/web`），外加程序化的
HTTP API（66 路由）。`zimeiti-api` 这个 console script 只是起 uvicorn 的启动器
（`argparse` 仅 `--port/--host`），**不是** CLI 工具。实际后果：

- 想看一眼用量/执行记录要开浏览器；
- 临时跑一句（「今天的 AI 热点」）要么开网页要么手写 curl + SSE 解析；
- 运维/调试（重启后确认服务活着）没有一个秒级命令。

自主运营闭环（autonomous 四变更）让链路能自己跑，但**人从外部介入只能靠网页**。

## What Changes

- 新包 `apps/api/zimeiti_cli/`（与 harness/api/autonomous 平级，**纯客户端，零业务逻辑**）：
  - `client.py`：HTTP 客户端（urllib 实现，**不引第三方依赖**）+ SSE 流式读取
  - `cli.py`：argparse 子命令
- console script：`zimeiti = zimeiti_cli.cli:main`（注册进 apps/api/pyproject）
- 子命令（默认 `http://127.0.0.1:8000`，`ZIMEITI_API`/`--base` 可覆盖）：

| 命令 | 行为 |
|---|---|
| `zimeiti chat "消息" [--session id]` | 流式打印回复（token/activity/error 帧）；LLM 凭据留在服务端 |
| `zimeiti flows` / `zimeiti flows new --name N --steps discover,plan [--schedule 08:00]` | 流程列表 / 新建 |
| `zimeiti flows run <id>` | 立即执行一次（**会真实消耗模型额度**——帮助文本与确认提示如实写明） |
| `zimeiti runs [--flow id]` | 执行记录（逐步明细） |
| `zimeiti usage` | 用量与折算金额（无单价时如实显示未折算） |

## Non-Goals

- **不做 IM 通道**（微信/飞书/企微）：用户已确认先不做，另行评估
- **不做服务端能力**：CLI 只调既有 HTTP API，零新端点（路由数不变——verify 守卫不会红）
- 不做交互式 REPL（单次命令式即可；要做也是后续独立变更）

## Capabilities

### New Capabilities

- `cli-entry-point`：提供命令行入口，使对话、运营流程管理、执行记录与用量可
  在不开浏览器的情况下完成；流式输出与 Web 端一致的 SSE 契约

## Impact

新增 `zimeiti_cli` 包 + 一个 console script；Makefile/pyproject 的 lint/type/security/
coverage 范围纳入新包；既有 Web/API/自主运营行为零变化（零新端点）。

```

## docs/openspec/changes/cli-entry-point/design.md

- Source: docs/openspec/changes/cli-entry-point/design.md
- Lines: 1-59
- SHA256: 95aab25af39b9eba71252bc3314b2d114cd4f81751956786d9824f3dcd6c59b4

```md
---
comet_change: cli-entry-point
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：cli-entry-point

## 高层方案

```
apps/api/zimeiti_cli/
  client.py     HTTP 客户端（urllib，零三方依赖）
                - get/post/delete：统一 Origin 头 + JSON 解析 + 可行动错误
                - sse_chat()：读 /api/chat/stream，逐帧 yield (event, data)
                - ApiError 带 status/body——把 4xx/5xx 翻成中文可读
  cli.py        argparse 子命令树
                chat / flows(list|new|run) / runs / usage
                chat 流式打印：token→stdout 无换行累积；activity→stderr 灰字；
                error→stderr 红字 + 非 0 退出
```

## 关键决策

### D1：纯客户端，零新端点
CLI 只调既有 API（`/api/chat/stream`、`/api/flows*`、`/api/flows/runs`、
`/api/autonomous/status`、`/api/usage`）。**不加任何服务端路由**——路由数不变，
`make verify` 的守卫不会因本变更误报（这是「入口 vs 能力」的边界自觉）。

### D2：urllib 而非 requests/httpx
仓库 API 侧已用 requests，但 CLI 是给开发者的轻工具：stdlib 实现让
`pip install zimeiti-cli` 零依赖，也让 CI 门禁（bandit/ruff）面最小。
SSE 用 `resp.readline()` 逐行读——与 Web 端同契约，无库可用恰好避免过度封装。

### D3：凭据留在服务端
CLI 的 chat 走服务端 API，**不读 OPENAI_API_KEY**。本地裸调模型是 Web/API
早已封死的路径（key 轮换、fallback、门禁都在服务端），CLI 复制一份只会漂移。

### D4：`flows run` 明示成本
立即执行真实消耗 token。子命令 help 里写明，且执行后回显 summary。
不设确认提示（开发者工具，多一次回车反而烦）——但 help/文档必须诚实。

### D5：退出码契约
0=成功；1=API 错误（含连接失败，附行动指引）；2=用法错误（argparse 默认）。
脚本里好判断，且与 CLI 惯例一致。

## 风险与对策

- **风险**：SSE 长连接中途断网 → 读超时（默认无超时）+ 服务端 30min TTL；
  CLI 给 `--timeout` 覆盖，断流时打印已收到的部分并提示重试
- **风险**：Windows GBK 终端炸在中文/emoji → 输出前 `sys.stdout.reconfigure`
  （UTF-8, errors=replace）——E2E 目检过的最小处理
- **风险**：与 `zimeiti-api` console script 命名混 → CLI 定名 `zimeiti`，
  帮助文本首行写明「zimeiti 命令行入口（连接已有后端）」

## Open Questions

无。

```

## docs/openspec/changes/cli-entry-point/tasks.md

- Source: docs/openspec/changes/cli-entry-point/tasks.md
- Lines: 1-17
- SHA256: e2b89614b7fc29ae6bac451bd5d715bf011dc5a8fde16b59401079cce569c25f

```md
---
comet_change: cli-entry-point
---

# Tasks：cli-entry-point

## 1. 客户端与命令树

- [ ] 1.1 client.py：urllib HTTP（统一错误）+ SSE 流式读取；单测（含错误翻译/连接失败行动指引） <!-- comet-task:7f70378c-b1f6-4e84-a1a5-077e27a146ee -->
- [ ] 1.2 cli.py：chat/flows/runs/usage 子命令 + 退出码契约 + UTF-8 输出保护 <!-- comet-task:7066ade5-242d-4e69-a0c9-7dc780fee50c -->
- [ ] 1.3 console script 注册（apps/api/pyproject）+ Makefile/pyproject 检查范围纳入 <!-- comet-task:e3249684-6203-416f-8c97-efcc6483980f -->

## 2. 验证与文档

- [ ] 2.1 单测（客户端/命令树/参数解析/SSE 帧解析，mock 传输） <!-- comet-task:5c979a79-5413-465f-9980-584f2ebb45dd -->
- [ ] 2.2 探针：真实服务上跑 flows 列表/新建/删除 + usage + runs（不烧 token） <!-- comet-task:eeaf1eee-80dd-4f56-bca7-866bced42cd4 -->
- [ ] 2.3 README 补「命令行入口」章节；make check 全绿 + E2E 不回归 <!-- comet-task:af3af4c3-6ba3-495f-b36b-d0c4b7d722d7 -->

```

## docs/openspec/changes/cli-entry-point/.openspec.yaml

- Source: docs/openspec/changes/cli-entry-point/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/cli-entry-point/specs/cli-entry-point/spec.md

- Source: docs/openspec/changes/cli-entry-point/specs/cli-entry-point/spec.md
- Lines: 1-48
- SHA256: 6275c9a9f2006ab1ec83503aae373ba3df82d56b47a8d698e4352646b8005857

```md
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

```
