---
change: agent-subagents-output
design-doc: docs/openspec/changes/agent-subagents-output/design.md
base-ref: 1f3c2f9
archived-with: 2026-10-17-agent-subagents-output
---

# Plan：专属子代理与结构化输出

<!-- comet-task-authority: docs/openspec/changes/agent-subagents-output/tasks.md -->

## G1 子代理定义 <!-- comet-task-ref:1620439c-b5d7-434b-bb81-ea9a263d0f85 -->

_build_subagents()：research（拒全部写）+ draft（仅 outputs/**）；不传 tools 以继承
文件工具、天然拿不到 ask_human/exec_script/memory_*；越权面用 FilesystemPermission 收死。

## G2 装配与模型 <!-- comet-task-ref:e53bc1c6-8b8d-40ab-903a-fb6e3ecd0793 --><!-- comet-task-ref:19fafd30-bd0f-4241-a039-ab9532be9cc5 -->

_build_agent 传 subagents（空表→默认通用子代理）；spec 必带 model，
ZIMEITI_SUBAGENT_MODEL 配置时才降档；ZIMEITI_SUBAGENT_ENABLED=false 可关。

## G3 结构化输出 <!-- comet-task-ref:a364631c-ede7-4e70-9997-38a443a319f8 --><!-- comet-task-ref:2d3371b9-6452-42ff-a11c-c1ad5c7bbc73 --><!-- comet-task-ref:b611f39f-db5e-45e6-a198-dadb743020c5 -->

runtime/schemas.py TopicEvaluation；_build_structured_agent() 按 schema 建独立 graph
（进程内缓存）+ chat_structured()；主 agent 不设 response_format。

## G4 验证 <!-- comet-task-ref:acf155c2-bf3d-430f-9b43-5cc4c4a5912a --><!-- comet-task-ref:3427f8ef-2b18-4a63-a4c9-61368b9165be -->

确定性层补子代理边界断言（随 make check）；结构化探针 + 子代理派生探针；
make check + make evals 双绿。
