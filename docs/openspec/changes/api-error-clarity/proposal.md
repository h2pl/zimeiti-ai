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
