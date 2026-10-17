---
comet_change: autonomous-flow
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：autonomous-flow

## 高层方案

```
apps/api/zimeiti_autonomous/            # 第三包：自主运营（与 harness/api 并列）
  flows.py     五层步骤模板 + 步骤裁剪 + prompt 组装（上一步摘要作输入）
  runner.py    串行执行：逐步落记录 → 归档产出 → 失败即停
  store.py     flows / flow_runs / flow_steps 三表（幂等建表）
  router.py    /api/flows CRUD + run-now（本变更只做后端）

zimeiti_api/automations/
  store.py     kind 增加 'flow'（payload = 流程 id）
  scheduler.py 分发：flow → autonomous.runner.run_flow（经注入的入口）

app.py         set_agent_entry(harness.ask_sync) 注入 + 建表
```

## 关键决策

### D1：步骤是「五层流程的固定枚举」，不是任意 DAG
用户要的是运营链路，不是通用工作流引擎。步骤枚举
`discover|plan|produce|publish|review`，流程即「这个枚举的非空有序子集」——
配置面极小（勾选即可），语义与既有五层技能一一对应，避免过度设计成 DAG 引擎。

### D2：逐步串行的输入传递 = 上一步产出摘要
每步 prompt = 该层技能的流程指令 + 全局配置（主题/平台/是否只到草稿）+
上一步产出摘要（截断，防 token 膨胀）。完整产出不进 prompt，只落文件。

### D3：agent 入口注入，包内不 import harness
`zimeiti_autonomous` 属业务侧，但按本仓既有纪律（personas/scheduler）走注入：
`runner.set_agent_entry(fn)`；未注入时抛明确错误。分层守卫（tests/test_layering.py）
后续可把 autonomous 纳入扫描范围。

### D4：失败即停 + 如实记录（护栏不在此变更）
重试、连续失败熔断、成本上限、自主模式 HITL 放行策略都归 `autonomous-guardrails`。
本变更只保证「失败停在第 N 步、原因可见、不吞异常」——先把骨架做对，不提前做策略。

### D5：复用既有调度通道，不新起调度器
`automations/scheduler.py` 已有 cron 解析、租约防重、执行记录与归档目录约定。
新增 `kind=flow` 分发分支即可，零新机制（对齐 model-cost-rotation 复用
FallbackChatModel 的做法）。

## 风险与对策

- **风险**：长链路耗时（一步可能数十秒）→ 与既有 prompt 任务一致走
  `run_in_executor` 投线程池，不阻塞调度 tick（本变更沿用 scheduler 现成做法）
- **风险**：产出摘要过长撑爆上下文 → 摘要截断（上限字符数），完整内容只落文件
- **风险**：`publish` 步在自主模式下触发 HITL 付费门卡住 → 本变更不处理
  （护栏变更解决）；流程默认步骤集不含 publish，需用户显式勾选

## Open Questions

无。
