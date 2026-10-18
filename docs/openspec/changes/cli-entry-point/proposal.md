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
