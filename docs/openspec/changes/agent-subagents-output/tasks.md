---
comet_change: agent-subagents-output
---

# Tasks：专属子代理与结构化输出

## 1. 子代理定义与装配

- [x] 1.1 `_build_subagents()`：research（只读工具+`ZIMEITI_SUBAGENT_MODEL`）+ draft（写工具、无 ask_human/exec_script）；`ZIMEITI_SUBAGENT_ENABLED` 可关 <!-- comet-task:1620439c-b5d7-434b-bb81-ea9a263d0f85 -->
- [x] 1.2 `_build_agent` 传入 subagents；子代理 prompt 写明回报契约（只查不写 / 写完报路径字数不发布） <!-- comet-task:e53bc1c6-8b8d-40ab-903a-fb6e3ecd0793 -->
- [x] 1.3 单测：子代理工具面不含禁用工具；开关生效；未设子代理模型时不传 model 字段 <!-- comet-task:19fafd30-bd0f-4241-a039-ab9532be9cc5 -->

## 2. 结构化输出

- [x] 2.1 `runtime/schemas.py`：TopicEvaluation（维度分/综合结论/建议） <!-- comet-task:a364631c-ede7-4e70-9997-38a443a319f8 -->
- [x] 2.2 `chat_structured()` 轻量入口：按 schema 建临时 graph（进程内缓存），不污染主对话 <!-- comet-task:2d3371b9-6452-42ff-a11c-c1ad5c7bbc73 -->
- [x] 2.3 单测：schema 字段与类型约束；未启用结构化时主对话行为不变 <!-- comet-task:b611f39f-db5e-45e6-a198-dadb743020c5 -->

## 3. 验证

- [x] 3.1 确定性断言补：子代理在册且工具面符合约束（并入 evals 确定性层） <!-- comet-task:acf155c2-bf3d-430f-9b43-5cc4c4a5912a -->
- [x] 3.2 make check + make evals 双绿；探针：探索类任务确实派了 research 子代理 <!-- comet-task:3427f8ef-2b18-4a63-a4c9-61368b9165be -->
