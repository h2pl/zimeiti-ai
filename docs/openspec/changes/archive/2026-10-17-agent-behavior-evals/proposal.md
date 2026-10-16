---
comet_change: agent-behavior-evals
---

# agent-behavior-evals：agent 行为回归套件

## Why

六个变更（五层流程 / 命令执行 / 前端债 / 操作契约 / 记忆 / 韧性）的行为结论**全部靠手工探针验证，跑完即焚**——每次我起测试服务、发一条真实 LLM 请求、肉眼判断「路由命中了吗 / 付费确认了吗 / 记忆跨会话了吗」，然后清理数据。证据留在验证报告里，**没有任何可重复执行的断言**。

后果是：下次谁改一句 SYSTEM_PROMPT、加一个工具、调一次技能目录注入，没人能证明行为有没有退化。单测覆盖的是函数（exec 白名单、记忆存储、fallback 判定），覆盖不到「agent 面对真实任务时的实际行为」；UI E2E 覆盖的是界面，不是 agent 决策。这中间有一层**行为回归的真空**。

实证：当前 `create_deep_agent(` 未传 `subagents`/`response_format`，工具清单来自 `_build_tools()`——任何一处改动都会改变行为，而现在没有任何自动化能捕获这种改变。

## What Changes

- 新增 `apps/api/tests/evals/`（行为回归套件，与单测分离）：
  - **确定性层**（无 LLM，可进 `make check`）：工具可发现性（技能目录含目标技能）、契约段在位（执行偏向/follow-through/ask-first/记忆节）、白名单拒绝、fallback 判定矩阵——这些都是纯函数断言，秒级
  - **行为层**（真实 LLM，`make evals` 单独跑，需 OPENAI_API_KEY）：把五个手工探针脚本化成断言——① 选题评估路由到详细技能；② 付费操作触发 ask_human；③ 清晰可逆任务直执行不提问；④ 跨会话记忆检索命中并带溯源；⑤ 主模型坏端点时自动切换且完成回复
- `Makefile` 加 `evals` 目标（起独立端口实例 → 跑行为层 → 清理演示数据 → 退出码即结果）；无 API key 时明确 SKIP 而非失败
- 行为层断言用「关键词命中 + 工具调用轨迹」双证据，避免脆弱的字面量断言；每条用例输出耗时与证据摘要，便于人工复核

## Capabilities

### New Capabilities

- `agent-behavior-evals`：agent 行为可重复回归——确定性层随门禁跑，行为层一条命令跑完并给出通过/失败与证据

## Non-Goals

- 替代单测或 UI E2E（三者分层，互不覆盖）
- 离线桩模型的全量行为仿真（桩模型的"通过"不代表真模型行为，价值有限）
- 打分式评测（LLM-as-judge）——先用确定性断言，judge 留后续
- 性能/延迟基线
