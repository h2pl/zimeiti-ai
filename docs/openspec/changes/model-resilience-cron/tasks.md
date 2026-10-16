---
comet_change: model-resilience-cron
---

# Tasks：模型韧性与定时自动化

## 1. 模型 fallback

- [ ] 1.1 FallbackChatModel wrapper（只对连接/限流/5xx 切换；4xx 直抛）+ 单测（RED→GREEN） <!-- comet-task:5d6f6011-9365-4f42-b9ae-b09c86958426 -->
- [ ] 1.2 `_build_model()` 接入：主模型 + `ZIMEITI_FALLBACK_MODELS` 链；设置面板显式选择的模型不 fallback <!-- comet-task:629a450b-465e-44d9-9bc4-17a981b573be -->
- [ ] 1.3 切换时活动行提示（用户可见） <!-- comet-task:6db22f98-a348-4b49-8b54-e958caf51dd9 -->

## 2. 定时自动化

- [ ] 2.1 `zimeiti_api/automations/`：PG 表 + CRUD 端点（/api/automations） <!-- comet-task:5598dedb-96db-496d-bfa9-a75db5854b5e -->
- [ ] 2.2 lifespan 调度循环（每分钟 tick，next_run 持久化+租约） <!-- comet-task:90f9bef0-2390-488e-b394-0e7d8b1284b9 -->
- [ ] 2.3 执行链路：kind=case（to_thread 跑 run_brand_case）/ kind=prompt（ask_sync）；日志落 outputs/_automations/ <!-- comet-task:58f6c6c2-8a5f-4e1c-8216-b5c94007656e -->

## 3. usage 统计

- [ ] 3.1 chat_usage 表 + 每轮记录（模型/token）+ /api/usage 查询端点 <!-- comet-task:1a88d55e-01a3-4725-a198-d2fd7121de07 -->
- [ ] 3.2 单测 + 探针（fallback 触发可观测） <!-- comet-task:fd549b82-7e17-4212-a7f9-e4625c47d657 -->

## 4. 验证

- [ ] 4.1 make check 全绿；探针：主模型指向坏端点 → 自动切备用且对话完成 <!-- comet-task:e9a54255-ec00-494e-9d02-430368c7fde2 -->
- [ ] 4.2 配置每日自动化 → tick 触发执行 → 日志可查；重启后任务仍在 <!-- comet-task:4ed7e3e4-bbc8-4762-b083-3bc812b285bc -->
