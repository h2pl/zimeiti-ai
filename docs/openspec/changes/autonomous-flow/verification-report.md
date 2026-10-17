---
comet_change: autonomous-flow
---

# 验证报告：autonomous-flow（运营流程编排）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 定义一条「发现+选题」的每日流程 | ✅ | 单测 `test_step_enum_and_validation` / `test_validate_steps_preserves_given_order`；探针「创建流程」（id 3e176ff57fd5） |
| 到点跑完整链路（逐步执行+记录+归档） | ✅ | 单测 `test_run_flow_serial_with_summary_chain`；探针：三步全部完成 + 摘要链 + 归档 `01-discover.md/02-plan.md/03-review.md` |
| 单步失败即停 | ✅ | 单测 `test_run_flow_stops_on_failure`；探针断言 `failed_step=plan` 且入口只被调用 2 次（第三步未执行） |
| agent 入口未注入时显式报错 | ✅ | 单测 `test_run_flow_requires_injected_entry`（RuntimeError 含「agent 入口未注入」）；分层守卫 `test_autonomous_package_does_not_import_harness` 扫包零命中 |
| 既有 case/prompt 行为零变化 | ✅ | 单测 `test_scheduler_dispatches_flow_kind`（三个分发函数并存）；E2E 63/63 无回归 |

## 自动化验证

- **单测 8 项**（RED→GREEN）
- **端到端探针 PASS**（真实服务 + 注入假入口，不消耗 token）：步骤目录 / 创建流程 /
  三步串行 / 上一步摘要注入下一步 / 逐步产出归档 / 失败即停 / 清理
- **make check**：exit 0，**246 passed**
- **E2E 全量**：63/63、双端差异 0

## 连带修复与发现

- `make verify` 路由数守卫如期拦下新增端点：期望值 57 → **61**（`/api/flows`、
  `/api/flows/{id}`、`/api/flows/{id}/run`、`/api/flows/steps/catalog` 四条）——
  这正是 stale-process-guard 变更把 verify 收编进 check 的价值
- Makefile / pyproject 的 ruff / mypy / bandit / coverage 范围纳入新包
- 过程中修：`_run_flow` 初版写成 `async def` 却被 `asyncio.to_thread` 调用（mypy 拦下），
  改为同步函数（长链路走线程池，与 case 一致，不阻塞调度 tick）

## 已知边界（留给后续变更）

- 失败**只停不重试**：重试 / 连续失败熔断 / 成本上限 / 自主模式 HITL 放行策略归
  `autonomous-guardrails`
- 无数据回流：复盘结论尚未喂回下一轮选题 → `autonomous-feedback`
- 无前端看板：仅后端 API + 探针 → `autonomous-observability`
