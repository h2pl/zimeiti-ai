---
comet_change: agent-memory-system
---

# Tasks：agent 记忆系统

## 1. 存储层（apps/api zimeiti_api/memory/）

- [x] 1.1 `store.py`：PG 表 memory_entries + memory_injections（DDL 幂等，进 pg.setup）；record/search/mark_injected/is_injected 函数 <!-- comet-task:78152964-2d99-402a-978a-9957eca09129 -->
- [x] 1.2 `tools.py`：memory_record / memory_search LangChain 工具（docstring 含使用纪律：凝练后先征询用户、一次性内容不记） <!-- comet-task:072f58fe-0faa-4804-a67b-b2d65448f43e -->
- [x] 1.3 `flush.py`：compaction 前 episodic flush（消息数>30 时截断最后 6 条前 500 字，origin=system，零 LLM 成本） <!-- comet-task:57c66339-0709-4150-bc2c-2e44a5885220 -->
- [x] 1.4 接入 `_build_agent`（tools 注册）+ ask() 挂 flush 钩子 + 会话删除级联清 injections <!-- comet-task:c917d698-90b1-4065-b10a-34a4e4789ad6 -->

## 2. 契约段

- [x] 2.1 SYSTEM_PROMPT【记忆】节：凝练-征询-确认流程、一次性内容不记、[记忆:origin] 标注使用、画像边界两条 <!-- comet-task:93f1eb29-3557-4175-8a09-172c197bfee6 -->

## 3. 验证

- [x] 3.1 单测：record/search/注入去重/越权 origin 拒绝（TDD RED→GREEN） <!-- comet-task:0fcf980a-e16c-4201-8c00-13716e5fad14 -->
- [x] 3.2 探针：跨会话检索上一轮凝练的经验（两会话） <!-- comet-task:2ffea3a5-2b66-4a77-a5de-d487e25d2176 -->
- [x] 3.3 make check 全绿 + E2E S05 无回归 <!-- comet-task:a24dc71e-ecc8-413e-a33c-59907f9c43d0 -->
