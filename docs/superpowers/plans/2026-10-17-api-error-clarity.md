---
change: api-error-clarity
design-doc: docs/openspec/changes/api-error-clarity/design.md
base-ref: 764af27
archived-with: 2026-10-17-api-error-clarity
---

# Plan：API 非 JSON 响应可读报错

<!-- comet-task-authority: docs/openspec/changes/api-error-clarity/tasks.md -->

## G1 request() 防线 <!-- comet-task-ref:d61bdfd2-db8d-4005-bdb0-4d47dd76678a --><!-- comet-task-ref:9a53914b-7d6e-4464-af09-fd6337499f08 -->

Content-Type 校验（D1）+ 可行动中文文案（D2）；端点面核查（SSE/文件不经此函数）。

## G2 验证与文档 <!-- comet-task-ref:1ea86dc6-bf17-49ce-9fcd-8b3fe680fb8c --><!-- comet-task-ref:ae3175e1-dacc-4596-aec5-9df6c8f8f875 --><!-- comet-task-ref:9534090e-94e7-4260-a1e7-147587d9aa9b -->

Playwright route 注入 HTML 探针（D3，含时序坑：默认页需 reload）；README 故障排查；
tsc/build/probe/make check 四验。
