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
