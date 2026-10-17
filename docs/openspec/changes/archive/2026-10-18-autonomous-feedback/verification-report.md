---
comet_change: autonomous-feedback
---

# 验证报告：autonomous-feedback（发布数据回流）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 有发布事实 → 汇总 | ✅ | 单测 `test_collect_published_with_facts`（2 条、平台 wechat） |
| 无发布事实 → 空结果不报错 | ✅ | 单测 `test_collect_published_empty_is_not_error` |
| 坏 JSON 容错 | ✅ | 单测 `test_collect_published_tolerates_bad_json`；探针「汇总跳过坏文件」items=2 |
| 校准信号只陈述事实 | ✅ | 单测 `test_build_calibration_states_facts_only`（断言不含 阅读数/CTR/点赞数/10万+） |
| 无数据时如实说明 | ✅ | 单测 `test_build_calibration_empty_says_so`；探针「无数据如实降级」 |
| 仅 discover 注入 | ✅ | 单测 `test_feedback_only_in_discover_prompt` / `test_runner_injects_feedback_into_discover`；探针断言 produce 步不含 wechat |
| 归档与查询 | ✅ | 单测 `test_context_for_discover_archives`；探针 `/api/feedback` 返回 calibration/has_facts |

## 自动化验证

- **单测 9 项**（RED→GREEN）
- **端到端探针 PASS**：坏文件容错 / discover 含校准段 / produce 不含 / 归档落盘 /
  无数据如实降级 / `/api/feedback` 可查
- **make check**：exit 0，**255 passed**
- **E2E 全量**：63/63、双端差异 0
- **门禁再次立功**：`make verify` 路由数守卫如期拦下 `/api/feedback`（61→62）

## 已知边界

- **不做平台阅读数拉取**（沿用 ops_analytics 决策 D2）：校准信号只含「发过什么」，
  有表现数据时再扩展消费，当前绝不虚构数值
- **不做评分/排序**：信号是事实摘要与缺口提示，非推荐权重
- 失败重试 / 熔断 / 成本上限 / 自主模式 HITL 放行 → `autonomous-guardrails`
- 前端看板与告警 → `autonomous-observability`
