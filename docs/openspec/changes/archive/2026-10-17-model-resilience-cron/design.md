---
comet_change: model-resilience-cron
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-17-model-resilience-cron
status: final
---

# 设计：模型韧性与定时自动化

## 高层方案

```
_build_model()（改造）
  ├─ 读 .env 主模型 + ZIMEITI_FALLBACK_MODELS（逗号分隔，可空）
  ├─ 用户显式选择（设置面板存的显式模型）→ 不 fallback
  └─ 包装 FallbackChatModel：invoke/astream 失败（连接/限流/5xx）→ 链下一个
       （自写 wrapper，不用 langchain 的 with_fallbacks——它不区分错误类型，
         会把 4xx 参数错误也切走，掩盖真实问题）

automations（新模块 zimeiti_api/automations/）
  ├─ PG 表 automations(id, name, cron/时刻, kind[case|prompt], payload, enabled,
  │                last_run, next_run, created_at)
  ├─ lifespan 起调度循环（asyncio，每分钟 tick，到点触发）
  └─ 触发执行：kind=case → asyncio.to_thread 跑 run_brand_case 主函数；
      kind=prompt → 经 ask_sync 走对话链路；结果写 outputs/_automations/<id>/

usage（pg.py 加表 chat_usage(session_key, turn_id, model, prompt_tokens,
      completion_tokens, created_at)）+ /api/usage 查询端点
```

## 关键决策

### D1：fallback 自写 wrapper 而非 with_fallbacks
langchain 的 `with_fallbacks` 对任何异常都切换。我们只对**基础设施类失败**
（APIConnectionError / RateLimitError / 5xx APIStatusError）切换；4xx（参数/鉴权）
直接抛——鉴权失败切备用模型只会把错误藏起来。

### D2：调度用进程内 asyncio tick 而非外部 cron
单用户本地服务，进程内每分钟 tick 足够；任务持久化在 PG 保证重启不丢；避免引
外部依赖（APScheduler 等）。执行与 API 进程同生命周期——服务停了任务不跑
（本地场景可接受，文档注明）。

### D3：定时任务的执行隔离
case 类任务 to_thread 跑（阻塞型脚本，已有成熟实现）；prompt 类任务走
ask_sync（主循环）。两者都写执行日志到 outputs/_automations/。

### D4：usage 只记 token 不换算钱
无单价数据源（OpenClaw 的阶梯定价引擎依赖其 model catalog；我们的模型是
.env 配置的任意端点）。记 token 数+模型名，金额换算留给未来接单价后做。

## 风险与对策

- **风险**：fallback 掩盖主模型配置错误 → 对策：4xx 不切换 + 切换时活动行提示
- **风险**：调度 tick 与服务重启竞态 → 对策：next_run 持久化 + 执行标记（running
  状态带租约时间），重启后过期租约任务重排
- **风险**：定时 case 跑失败无声 → 对策：执行日志落盘 + 失败写入 automation_runs

## Open Questions

无。
