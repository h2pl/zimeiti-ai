---
comet_change: autonomous-observability
---

# 验证报告：autonomous-observability（自主运营看板）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 执行记录可查（含步骤明细） | ✅ | 单测 `test_list_runs_contains_steps`（步骤序列/状态）、`test_list_runs_captures_failed_step`（失败步骤与错误入记录）、`test_list_runs_limit_respected` |
| 看板四要素可见 | ✅ | E2E S13 断言：流程列表（创建+步骤徽标+调度）、执行记录区、运行状态卡（当日预算/待确认/熔断）；单跑两连 6/6 |
| 新建流程勾选步骤 | ✅ | S13：勾选「创作」后保存 → 列表卡片显示 发现/选题/创作 三个徽标 + 每天 08:00 |
| 样式沿用既有体系 | ✅ | 三态截图目检（空态/表单/列表）——page-title/panel/field/btn/badge/card/foot-note 全在体系内；自定义 CSS 仅 `.auto-steps/.auto-step` 两行全 token |
| E2E 13 场景 | ✅ | 全量 **69/69**、双端差异 0、NOTE 6（S11/S12/S13 zimeiti 独有为预期差异） |

## 过程中抓出的真 bug（诚实记录）

**createFlow POST 422**：`request()` 默认不带 `Content-Type`，既有 POST 封装都显式
设置——新封装漏了导致 body 被 FastAPI 当作字符串（`Input should be a valid
dictionary`），页面表现为「保存无反应」。**Playwright response 监听取证**（post_data
与响应体对照）才定位。修复后截图复验 POST 200、表单关闭、卡片入列。

这正是「必须严格测试」的价值：功能测试（单测/E2E）全绿也拦不住这类**集成层**
问题——只有真实浏览器点一遍才暴露。

## 自动化验证

- **单测 3 项**（执行记录读侧）
- **E2E 全量**：13 场景 **69/69**、双端差异 0（S13 两连跑稳定）
- **make check**：exit 0，**268 passed**（verify 路由期望 63→64，守卫第四度立功）
- **make evals**：5/5（真实 LLM 行为层）
- **demo 第 6 段**录制完成（06-autonomous.mp4），演示数据自动清理

## 已知边界

- 无告警推送（IM/邮件）：blocked 与熔断在页面可见，推送后续再议
- 「立即执行」按钮刻意不提供（真实消耗额度）；流程由调度器到点执行
