---
comet_change: harness-business-split
---

# 验证报告：harness-business-split（harness 与业务分层）

## 分层事实（重构后）

| 检查 | 结果 |
|---|---|
| harness 源码业务域 import | **0**（tests/test_layering.py 扫描全源码，含函数级延迟 import） |
| harness 对 zimeiti_api 的引用 | 仅 `zimeiti_api.core.*`（共享 infra 白名单） |
| business→harness agent 入口 | 0 硬 import（personas/scheduler 均走组装层 setter 注入） |
| `zimeiti_api/runtime/` | 已消失；chat/status 归位为顶层路由 |

## 自动化验证

- **make check**：exit 0，**234 passed**（含 5 项新分层守卫：包结构落位/业务域
  零 import/core 白名单/scheduler 注入纪律/contract roundtrip）
- **E2E 全量**：**63/63、双端差异 0**（MockLLM——浏览器级行为零变化）
- **mypy/ruff/bandit**：harness 纳入全部检查范围（50 文件 0 问题）

## 已知阻塞（非回归）—— 已解除

- ~~**make evals 5/5 暂阻~~ → **已充值复跑确认：5/5 passed（72.6s）**。
  阻塞期间 5 条行为用例全部因 **DeepSeek 402 Insufficient Balance** 失败
  （request_id 4ca4b7ae 等）——账户计费问题，非重构回归；402 正确地未触发
  fallback（4xx 直抛设计）。等价性在阻塞期间已由 E2E（MockLLM 全链路）+
  确定性层（契约/工具/提示词断言）背书，充值后复跑补齐最后一环。

## 过程发现

- 守卫正则 `\s*` 配 re.M 会跨行吞噬空行导致行定位为空——改 `[ \t]`（已记录在
  测试注释）
- app.py 组装注入点集中在 import 区后的一小段（personas/scheduler/skills
  provider 三处），分层规则第一次有了机械守卫而非口头约定
