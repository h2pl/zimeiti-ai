---
comet_change: autonomous-guardrails
---

# 验证报告：autonomous-guardrails（无人值守护栏）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 可重试异常被重试 | ✅ | 单测 `test_retryable_exception_is_retried`；探针「重试至上限后失败」calls=3 retries=2 |
| 配置性错误不重试 | ✅ | 单测 `test_config_error_not_retried`（calls=1）、`test_is_retryable_classification` |
| 连续失败触发熔断 | ✅ | 单测 `test_circuit_breaker_trips_and_resets`（3 次跳闸） |
| 成功后计数归零 | ✅ | 同上（record_success 后 tripped=False、计数 0） |
| 超预算即停 | ✅ | 单测 `test_budget_guard_blocks_when_over`；探针断言 1.5>1.0 拦截、0.5 放行 |
| 无单价数据不拦截 | ✅ | 单测 `test_budget_guard_passes_when_unknown`（None → 放行） |
| 需确认动作不阻塞 | ✅ | 单测 `test_runner_marks_blocked_and_continues`；探针断言流程 status=done 且 produce 标 blocked、review 继续执行 |
| blocked 可见 | ✅ | `GET /api/autonomous/status` 返回 circuit/budget/blocked 三段 |

## 自动化验证

- **单测 10 项**（RED→GREEN），三个自主包测试共 27 项全过
- **端到端探针 PASS**：重试计数 / blocked 不阻塞 / 预算拦截与放行 / status 端点
  **读到真实用量**（`spent_usd` 字段来自注入的提供者）
- **make check**：exit 0，**265 passed**
- **E2E 全量**：63/63、双端差异 0（复跑确认；首轮 1 项为热点条目计数偶发）
- 门禁第三度立功：路由数守卫 62→63（新增 `/api/autonomous/status`）

## 过程中修正的两处（诚实记录）

1. **首版 `status()` 直接 import `zimeiti_harness.usage`**——违反本包「不 import
   harness」的分层纪律（且被既有单测 `test_autonomous_package_does_not_import_harness`
   盯住）。改为 `set_budget_provider` 注入，app.py 接线
2. **app.py 注入块未生效**：锚点被 ruff 折行后不匹配，补丁静默未插入——探针显示
   「用量提供者未注入」才暴露。已补插并复跑确认 `spent_usd` 有值
3. 闭包绑定循环变量（ruff B023）→ 默认参数绑定

## 已知边界

- 熔断阈值与重试次数为流程级配置，尚未接入前端（看板归 `autonomous-observability`）
- blocked 判定基于**结果侧特征词**（保守识别），宁可多标待办也不自作主张放行
