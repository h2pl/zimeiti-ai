# Comet Design Handoff

- Change: api-error-clarity
- Phase: design
- Mode: compact
- Context hash: e1167eddc1447abecffe0eb05fc63f150ada46078435fefd9850604f4ae14158

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/api-error-clarity/proposal.md

- Source: docs/openspec/changes/api-error-clarity/proposal.md
- Lines: 1-52
- SHA256: e72ff7317e987123609cb314f20e13b370573b6a9dda385f0bbdc8794b41fe12

```md
---
comet_change: api-error-clarity
---

# api-error-clarity：API 错误可读性与非 JSON 响应防线

## Why

用户实测报出两处不可读错误（用量卡片 + 自动化页）：

```
用量加载失败：Unexpected token '<', "<!doctype "... is not valid JSON
加载失败：Unexpected token '<', "<!doctype "... is not valid JSON
```

取证结论（现场复现）：

- **直接根因**：运行中的 vite dev（:5173）代理失效——`/api/*` 未被转发到 :8000，
  落进 vite 的 SPA 兜底返回 index.html（同配置的新起实例 5199 一切正常）。
  后端本身无恙（:8000 对 `/api/usage` 返回正常 JSON，未知 `/api/*` 返回 JSON 404）。
- **暴露的真缺陷**：`lib/api.ts` 的 `request()` 只检查 `res.ok`，对「200 + HTML」
  直接 `res.json()` → 抛出 `Unexpected token '<'` 这种用户无法行动的原始异常。
  任何「代理失效 / 后端未就绪 / 前后端版本不一致」的故障都会以此形态呈现。
- **验证盲区**：E2E 每次自起全新服务，永远测不到「运行中 dev 代理坏掉」这类故障；
  前端也没有任何单测设施拦截该缺陷。

## What Changes

- **前端 `request()`**：响应成功后按 `Content-Type` 校验是 JSON——非 JSON（如
  HTML）时抛出**可行动**的中文错误：「服务返回了 HTML 而非 JSON——API 代理/后端
  未就绪，或前后端版本不一致；请重启 make dev 或刷新页面」，而非原始 SyntaxError
- **README**：新增「故障排查」一节（dev 代理失效的表象/自查/处置），把这次的
  根因与处置路径沉淀为文档
- **Playwright 探针**：用 route 拦截把 `/api/usage` 篡改为 HTML 响应，断言用量
  卡片显示的是友好错误而非原始 token 信息（作为该缺陷的回归验证）

## Non-Goals

- 不改 vite 代理配置本身（当前配置正确，是运行实例的坏状态）
- 不做自动重试/轮询（错误信息可行动即可，重连已有既有逻辑）
- 不给前端引入测试框架（探针脚本复用 Playwright 即可）

## Capabilities

### New Capabilities

- `api-error-clarity`：API 响应为非 JSON 时，界面呈现可行动的中文错误而非原始解析异常

## Impact

`apps/web/src/lib/api.ts` 单点修改；`README.md` 增补故障排查；一个 Playwright
探针脚本；无后端改动。

```

## docs/openspec/changes/api-error-clarity/design.md

- Source: docs/openspec/changes/api-error-clarity/design.md
- Lines: 1-52
- SHA256: 106855b718e2cb73a258a9fd480ddf16328eab7e3913c99ca44eb617adce0b7f

```md
---
comet_change: api-error-clarity
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：API 错误可读性

## 高层方案

```
lib/api.ts request()
  const res = await fetch(...)
  if (!res.ok) { ...现有 detail 提取逻辑不变... }
  const ct = res.headers.get('content-type') || ''
  if (!ct.includes('application/json')) {
    throw new Error('服务返回了 HTML 而非 JSON——API 代理/后端未就绪，'
      + '或前后端版本不一致。请重启 make dev（或刷新页面后重试）。')
  }
  return res.json()
```

## 关键决策

### D1：校验 Content-Type 而非 try/catch res.json()
内容协商是「意图」层面的事实（后端永远回 JSON；回 HTML 一定是链路故障），
比 catch 解析异常更早、更准地定位问题类别。catch JSON.parse 只能给出
「解析失败」，无法区分「后端真坏了」还是「代理回了页面」。

### D2：错误信息给处置指引而非仅描述现象
这次事故里用户面对 `Unexpected token '<'` 完全无从下手。新文案直接告诉用户
两步：这是链路问题（不是你的操作问题）→ 重启 make dev。后端 JSON 404
（版本错位）则由现有 `!res.ok` 分支展示 `{detail}`，无需重复处理。

### D3：回归探针用 Playwright route 拦截，不引入前端测试框架
「后端返回 HTML」在真实链路里难以稳定复现（要人为弄坏 dev 代理），但
Playwright 可以精确注入这个场景：`route.fulfill(body: '<!doctype html>')`。
探针断言用量卡片渲染的是新文案且不含 `Unexpected token`。脚本放
`apps/scripts/probe_api_error.py`，与既有探针同范式，不进 make check
（前端无测试基建，这是本次明确的 Non-Goal）。

## 风险与对策

- **风险**：个别端点返回非标准 Content-Type 被误杀 → 已核查后端全部
  FastAPI JSONResponse 均带 application/json；SSE（chat/stream）不走 request()
- **风险**：FileResponse 类端点（如预览文件）也走 request()？→ 已核查：
  文件下载/预览由独立函数处理，不经 request()

## Open Questions

无。

```

## docs/openspec/changes/api-error-clarity/tasks.md

- Source: docs/openspec/changes/api-error-clarity/tasks.md
- Lines: 1-16
- SHA256: d53da4c0cce10d2923267c10cc913eb151dae013b94e14bd2b4475845e397e41

```md
---
comet_change: api-error-clarity
---

# Tasks：API 错误可读性

## 1. request() 防线

- [ ] 1.1 `lib/api.ts` request()：Content-Type 校验，非 JSON 抛可行动中文错误（D1/D2） <!-- comet-task:d61bdfd2-db8d-4005-bdb0-4d47dd76678a -->
- [ ] 1.2 排查确认：所有经 request() 的端点均返回 application/json；SSE 与文件端点不经此函数 <!-- comet-task:9a53914b-7d6e-4464-af09-fd6337499f08 -->

## 2. 验证与文档

- [ ] 2.1 Playwright 探针（apps/scripts/probe_api_error.py）：route 拦截注入 HTML → 断言友好错误呈现（D3） <!-- comet-task:1ea86dc6-bf17-49ce-9fcd-8b3fe680fb8c -->
- [ ] 2.2 README 故障排查一节：表象/自查（curl :8000/api/status 区分前后端）/处置 <!-- comet-task:ae3175e1-dacc-4596-aec5-9df6c8f8f875 -->
- [ ] 2.3 双验：npm build + tsc 通过；探针通过；make check 全绿（后端无改动，确认无回归） <!-- comet-task:9534090e-94e7-4260-a1e7-147587d9aa9b -->

```

## docs/openspec/changes/api-error-clarity/.openspec.yaml

- Source: docs/openspec/changes/api-error-clarity/.openspec.yaml
- Lines: 1-2
- SHA256: 4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9

```md
schema: spec-driven
created: 2026-10-17

```

## docs/openspec/changes/api-error-clarity/specs/api-error-clarity/spec.md

- Source: docs/openspec/changes/api-error-clarity/specs/api-error-clarity/spec.md
- Lines: 1-27
- SHA256: 7851dbad73f3b8b0e86e07451f46c0db01e3e061ab87fa88af53991947fb7ba8

```md
# api-error-clarity 规格草案

## Purpose

API 链路上的「200 + HTML」（代理失效/后端未就绪/版本错位）不再以原始
`Unexpected token '<'` 呈现给用户，而是给出可行动的中文错误。

## ADDED Requirements

### Requirement: 非 JSON 响应的可读报错

`request()` 对成功状态码的响应校验 Content-Type；非 JSON 时抛出可行动错误，
错误信息包含「收到 HTML」与处置指引（重启 make dev / 检查后端）。

#### Scenario: 代理失效返回 HTML
- **WHEN** `/api/*` 请求返回 200 且响应体是 HTML（如 vite SPA 兜底）
- **THEN** 调用方收到中文错误「服务返回了 HTML 而非 JSON……请重启 make dev
  或检查后端」，用量卡片/自动化页等显示该信息而非 `Unexpected token '<'`

#### Scenario: 正常 JSON 不受影响
- **WHEN** 响应为 JSON（成功或 FastAPI 错误格式）
- **THEN** 行为与现状完全一致

### Requirement: 故障排查文档

README 含「故障排查」一节：dev 代理失效的表象（页面报 HTML/JSON 错）、
自查方法（直接 curl :8000/api/status 区分前后端）、处置（重启 make dev）。

```
