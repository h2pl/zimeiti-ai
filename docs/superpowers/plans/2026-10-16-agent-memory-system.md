---
change: agent-memory-system
design-doc: docs/openspec/changes/agent-memory-system/design.md
base-ref: 37d1d6a
archived-with: 2026-10-16-agent-memory-system
---

# Plan：agent 记忆系统

<!-- comet-task-authority: docs/openspec/changes/agent-memory-system/tasks.md -->

## G1 存储层（TDD） <!-- comet-task-ref:78152964-2d99-402a-978a-9957eca09129 --><!-- comet-task-ref:072f58fe-0faa-4804-a67b-b2d65448f43e --><!-- comet-task-ref:57c66339-0709-4150-bc2c-2e44a5885220 -->

tests/test_memory.py RED → zimeiti_api/memory/store.py（memory_entries/memory_injections
DDL+record/search/mark_injected/is_injected）+ tools.py（memory_record/memory_search）+
flush.py（消息>30 截断最后 6 条前 500 字，origin=system）。

## G2 接线 <!-- comet-task-ref:c917d698-90b1-4065-b10a-34a4e4789ad6 --><!-- comet-task-ref:93f1eb29-3557-4175-8a09-172c197bfee6 -->

_build_agent 注册两工具；ask() 挂 flush；session 删除级联清 injections；
SYSTEM_PROMPT【记忆】节（凝练-征询-确认/一次性不记/[记忆:origin]标注/画像边界）。

## G3 验证 <!-- comet-task-ref:0fcf980a-e16c-4201-8c00-13716e5fad14 --><!-- comet-task-ref:2ffea3a5-2b66-4a77-a5de-d487e25d2176 --><!-- comet-task-ref:a24dc71e-ecc8-413e-a33c-59907f9c43d0 -->

单测 GREEN；两会话探针（跨会话检索经验）；make check + S05。
