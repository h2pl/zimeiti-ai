---
change: model-resilience-cron
design-doc: docs/openspec/changes/model-resilience-cron/design.md
base-ref: ee111cd
archived-with: 2026-10-17-model-resilience-cron
---

# Plan：模型韧性与定时自动化

<!-- comet-task-authority: docs/openspec/changes/model-resilience-cron/tasks.md -->

## G1 fallback（TDD） <!-- comet-task-ref:5d6f6011-9365-4f42-b9ae-b09c86958426 --><!-- comet-task-ref:629a450b-465e-44d9-9bc4-17a981b573be --><!-- comet-task-ref:6db22f98-a348-4b49-8b54-e958caf51dd9 -->

tests/test_model_fallback.py RED → runtime/model_fallback.py（FallbackChatModel：
只对 APIConnectionError/RateLimitError/5xx 切换，4xx 直抛）→ _build_model 接入
（ZIMEITI_FALLBACK_MODELS 链；设置显式模型不 fallback）→ 活动行切换提示。

## G2 automations <!-- comet-task-ref:5598dedb-96db-496d-bfa9-a75db5854b5e --><!-- comet-task-ref:90f9bef0-2390-488e-b394-0e7d8b1284b9 --><!-- comet-task-ref:58f6c6c2-8a5f-4e1c-8216-b5c94007656e -->

zimeiti_api/automations/（PG 表 + CRUD 端点）+ lifespan 调度循环（分钟 tick、
next_run 持久化+租约）+ 执行链路（case→to_thread 跑 run_brand_case；prompt→ask_sync；
日志落 outputs/_automations/）。

## G3 usage <!-- comet-task-ref:1a88d55e-01a3-4725-a198-d2fd7121de07 --><!-- comet-task-ref:fd549b82-7e17-4212-a7f9-e4625c47d657 -->

chat_usage 表 + run_turn 记录（模型/token）+ /api/usage 查询 + 单测。

## G4 验证 <!-- comet-task-ref:e9a54255-ec00-494e-9d02-430368c7fde2 --><!-- comet-task-ref:4ed7e3e4-bbc8-4762-b083-3bc812b285bc -->

探针：主模型坏端点→自动切换；自动化配置→触发→日志；make check。
