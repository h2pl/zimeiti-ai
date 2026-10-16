---
comet_change: model-resilience-cron
---

# model-resilience-cron：模型韧性与定时自动化

## Why

OpenClaw 源码调研（model-failover.md / automations）显示两块我们没有的能力：

1. **模型 fallback 链**：auth-profile 轮换→模型 fallback 链；**用户显式选择的模型严格不 fallback**。我们单一模型直连，主模型一挂（限流/欠费/网络）对话全断。
2. **定时自动化（automations/cron）**：会话级持久化的定时任务与心跳。用户提过「每天早上自动出稿」的运营 case 定时化需求，目前只能手动跑 `run_brand_case.py`。

另缺**会话成本可见性**（OpenClaw 有 usage 滚动统计；我们无任何 token/成本追踪）。

## What Changes

- `_build_model()` 支持 fallback 链：主模型不可用（连接错误/限流/5xx）自动切下一个；用户在设置里显式指定的模型**不** fallback（OpenClaw 同款语义）
- `automations` 端点 + 工具：CRUD 定时任务（cron 表达式或每日时刻），任务体=运营 case 脚本或预置 prompt；服务重启后任务不丢（PG 持久化）；到点执行经既有 ask/chat 链路
- 会话 usage 统计：每轮对话记录 token 用量（PG），`/api/usage` 可按会话/日期查

## Capabilities

### New Capabilities

- `model-fallback`：主模型故障自动切换备用模型，显式选择不降级
- `scheduled-automation`：定时运营任务持久化与到点执行
- `usage-tracking`：会话 token 用量记录与查询

## Non-Goals

- 阶梯定价/成本金额引擎（只记 token 数，不换算钱——无单价数据源）
- 订阅配额窗口与 provider usage 直拉（OpenClaw 的 usage-tracking 后半程）
- standing intents / Prospective 记忆层（②已声明不做）
- heartbeat 心跳协议（单用户场景用 cron 足够）
