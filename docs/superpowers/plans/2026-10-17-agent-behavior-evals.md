---
change: agent-behavior-evals
design-doc: docs/openspec/changes/agent-behavior-evals/design.md
base-ref: 4710fca
archived-with: 2026-10-17-agent-behavior-evals
---

# Plan：agent 行为回归套件

<!-- comet-task-authority: docs/openspec/changes/agent-behavior-evals/tasks.md -->

## G1 骨架与契约断言 <!-- comet-task-ref:e511638b-55f0-43ac-bf54-529d1fe116c1 --><!-- comet-task-ref:8435f1d9-0e9f-4802-8501-a26209014d06 -->

tests/evals/ 骨架 + conftest（端口/实例/清理/behavior 标记）+ 契约段在位断言
（人格/执行偏向/Follow-through/ask-first/编排纪律/五层索引/白名单/记忆/语言）。

## G2 目录与工具断言 <!-- comet-task-ref:fcbd4ba7-1417-4b80-939e-60bd7e6ab9a0 -->

技能目录含既有详细技能 + 路由链纪律 + layer 分组 + 提示词规模护栏；
工具在册（exec_script / memory_record / memory_search / ask_human）。

## G3 安全与 fallback 矩阵 <!-- comet-task-ref:fee480a9-d726-4bc4-8247-e5d0e3be3ec3 -->

白名单拒绝 + 路径注入拒绝 + fallback 判定矩阵（连接/5xx/429 可切换；4xx 直抛）。
踩坑：build_system_prompt 预热技能 TTL 缓存污染后续用例 → 加缓存清理 fixture。

## G4 行为层五条用例 <!-- comet-task-ref:b3d5dc20-b475-4f17-bbfa-7f181bf2c4d2 --><!-- comet-task-ref:cb3e344a-7633-40e6-a88d-27af01773882 --><!-- comet-task-ref:3348d410-0112-48b6-9740-498307797e3b --><!-- comet-task-ref:10a14805-ffd9-4fae-8216-2dfbee4dabf0 --><!-- comet-task-ref:8eae5e0a-f29f-422a-a820-ad16e30114dc -->

① 选题评估路由详细技能 ② 付费门不变量 ③ 可逆直执行 + 中文主导
④ 跨会话记忆检索 + 溯源 ⑤ fallback 切换（坏端点实例 + 日志断言）。
判据修订：付费门从「必须触发 ask_human」改为「确认前不发起付费调用」不变量。

## G5 门禁与清理 <!-- comet-task-ref:553489fa-5c1a-4c6e-9469-4c0be29899a0 --><!-- comet-task-ref:a8f284df-20e4-4164-8491-cc2fe97cf397 -->

无密钥时整体 SKIP（退出码 0）+ finally 清理演示数据；
Makefile evals 目标；check 用 -m "not behavior" 排除行为层。

## G6 双验 <!-- comet-task-ref:60808f23-59c8-4af3-9b43-27825d529ea2 -->

make check（含确定性层）+ make evals（五条全绿）双验。
