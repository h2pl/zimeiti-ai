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
