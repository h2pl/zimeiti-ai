# Comet Design Handoff

- Change: agent-memory-system
- Phase: design
- Mode: compact
- Context hash: b6ad57e6d5fea3cc648132723f044b4ebe72c776dd3bb71f617a76dc1444c84c

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/agent-memory-system/proposal.md

- Source: docs/openspec/changes/agent-memory-system/proposal.md
- Lines: 1-32
- SHA256: d44a2536f653c752f70d4ecd71a7d55baae298439888083104199a19078d7981

```md
---
comet_change: agent-memory-system
---

# agent-memory-system：agent 记忆系统

## Why

OpenClaw 源码调研（memory-architecture.md / dreaming.md）显示其最强差异化能力之一是**五层记忆架构**：Instructions（AGENTS.md）/ Curated core（MEMORY.md+USER.md，dreaming 后台固化）/ Episodic（memory/YYYY-MM-DD 日记）/ Prospective（standing intents）/ Review（DREAMS.md），且**溯源是安全边界**（每条记忆带 origin class：owner/agent/untrusted/system，SQLite provenance 列，模型无法经 prose 写入；recall-loop 预防——注入过的内容结构化标记，绝不重复抽取）。

我们现状：只有画像 memory.md（单文件、无检索、无溯源、无固化流程），会话历史在 PG checkpoint（非记忆）。后果：跨会话经验无法复用（「上次用户认可的封面风格」换会话就忘）；无沉淀机制（AGENTS.md 的「任务结束凝练 1-3 条询问是否写入画像」流程未接线）；记忆注入无溯源标记。

## What Changes

- 新增记忆模块（apps/api `zimeiti_api/memory/`）：PG 两张表（`memory_entries`：content/origin_class/scope/importance/tags/created_at；`memory_injections`：注入去重日志防 recall-loop）
- 新工具 `memory_record`（记录，origin=agent，需 importance≥阈值）+ `memory_search`（检索，带溯源标注输出）
- SYSTEM_PROMPT 契约段：任务结束凝练可复用经验（偏好/红线/技巧/归因）经 memory_record 落库；一次性规格不记；注入内容带 `[记忆:origin]` 标注
- compaction 前 flush：会话压缩前把关键上下文写入 episodic（对应 OpenClaw auto memory flush）
- 画像 memory.md 保持唯一用户画像长期记忆（不被全局记忆污染——OpenClaw AGENTS.md 第 95-96 条同款边界）

## Capabilities

### New Capabilities

- `agent-memory-system`：agent 跨会话记忆——可复用经验的记录/检索/溯源/防重复注入，与画像 memory.md 边界分明

## Non-Goals

- dreaming 多阶段后台固化（light→REM→deep）与 DREAMS.md review 层（后续变更）
- standing intents / cron  Prospective 层（batch ③ model-resilience-cron 的 automations 覆盖）
- 跨用户共享记忆（单用户工作台）
- OpenClaw 的 SQLite provenance 列等价物之外的记忆格式创新（内容存 PG，溯源用 origin_class 列）

```

## docs/openspec/changes/agent-memory-system/design.md

- Source: docs/openspec/changes/agent-memory-system/design.md
- Lines: 1-67
- SHA256: 3df9a106f4fc03ee7bbd8a934be9e1029c02030cc051ac4206588571c23e3c54

```md
---
comet_change: agent-memory-system
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：agent 记忆系统

## 高层方案

```
SYSTEM_PROMPT 契约段（新增【记忆】节）
  「任务结束出现可复用经验（偏好/红线/技巧/归因）→ 凝练 1-3 条征询用户 →
   确认后 memory_record；一次性规格不记；检索结果按 [记忆:origin] 标注使用」
        │ agent 调用
        ▼
zimeiti_api/memory/（新模块）
  ├─ store.py   PG：memory_entries(id, content, origin_class, scope, importance,
  │             tags[], created_at) + memory_injections(session_key, entry_id, injected_at)
  ├─ tools.py   memory_record(content, origin, importance, tags) / memory_search(query, limit)
  └─ flush.py   compaction 前 episodic flush（接 SummarizationMiddleware 前钩子或
               _load_messages 处会话加载时补记）
        │ 注册
        ▼
_build_agent tools += [memory_record, memory_search]
```

## 关键决策

### D1：存储用 PG 而非文件
checkpoint 与业务数据都在 PG（pg.py 已有连接池与表初始化范式），记忆表同库同管道；
文件方案（memory/YYYY-MM-DD.md）在 Windows 下并发写与检索都不如 SQL。Episodic
flush 的载体就是 memory_entries（scope=episodic）。

### D2：recall-loop 预防用注入日志表
OpenClaw 的做法是「注入过的内容结构化标记」。我们落为 `memory_injections`
(session_key, entry_id)：memory_search 在同一会话内过滤已注入条目；新会话重新
可注入（跨会话复用正是目的）。表带 TTL 清理（随会话清理走）。

### D3：compaction flush 的挂点
deepagents 的 SummarizationMiddleware 在摘要前后没有公开钩子 → 用**替代挂点**：
agent_runtime.ask() 在消息数超过阈值时（如 >30 条）先 flush 再放行摘要；
不修改 deepagents 内部。flush 内容 = 最近 N 条消息的一句话凝练（调一次轻量 LLM
调用？——不，改用确定性截断：取最后 6 条消息的 content 前 500 字，origin=system，
scope=episodic，零 LLM 成本）。

### D4：重要性阈值与用户确认
memory_record 的 importance 1-10；agent 侧≥7 才值得记（偏好/红线/被反复认可的
方法）；用户明确要求记的（owner）不受阈值限制。**所有记录都经用户确认**（对话中
凝练→征询→确认），没有后台静默写入——比 OpenClaw dreaming 的自动固化保守，
单用户场景确认成本低。

### D5：与画像边界
契约段明示两条：①记忆库不写画像 memory.md；②画像更新只经画像管理流程（用户确认）。
记忆搜索范围默认全 scope，但画像相关查询引导读 profiles/<画像>/memory.md。

## 风险与对策

- **风险**：提示词膨胀 → 对策：【记忆】节控制在 5 行内，细节在工具 docstring
- **风险**：注入日志表无限增长 → 对策：会话删除时级联清（已有 session 删除链路加一行）
- **风险**：flush 截断内容质量差 → 对策：scope=episodic + importance=3（低权重，
  检索排序靠后），只作保险不作主来源

## Open Questions

无。

```

## docs/openspec/changes/agent-memory-system/tasks.md

- Source: docs/openspec/changes/agent-memory-system/tasks.md
- Lines: 1-22
- SHA256: 6ece24565c90dbab5bc1f33b5e1992b2f341e5daca56bd5cd0d11b633f69dff5

```md
---
comet_change: agent-memory-system
---

# Tasks：agent 记忆系统

## 1. 存储层（apps/api zimeiti_api/memory/）

- [ ] 1.1 `store.py`：PG 表 memory_entries + memory_injections（DDL 幂等，进 pg.setup）；record/search/mark_injected/is_injected 函数 <!-- comet-task:78152964-2d99-402a-978a-9957eca09129 -->
- [ ] 1.2 `tools.py`：memory_record / memory_search LangChain 工具（docstring 含使用纪律：凝练后先征询用户、一次性内容不记） <!-- comet-task:072f58fe-0faa-4804-a67b-b2d65448f43e -->
- [ ] 1.3 `flush.py`：compaction 前 episodic flush（消息数>30 时截断最后 6 条前 500 字，origin=system，零 LLM 成本） <!-- comet-task:57c66339-0709-4150-bc2c-2e44a5885220 -->
- [ ] 1.4 接入 `_build_agent`（tools 注册）+ ask() 挂 flush 钩子 + 会话删除级联清 injections <!-- comet-task:c917d698-90b1-4065-b10a-34a4e4789ad6 -->

## 2. 契约段

- [ ] 2.1 SYSTEM_PROMPT【记忆】节：凝练-征询-确认流程、一次性内容不记、[记忆:origin] 标注使用、画像边界两条 <!-- comet-task:93f1eb29-3557-4175-8a09-172c197bfee6 -->

## 3. 验证

- [ ] 3.1 单测：record/search/注入去重/越权 origin 拒绝（TDD RED→GREEN） <!-- comet-task:0fcf980a-e16c-4201-8c00-13716e5fad14 -->
- [ ] 3.2 探针：跨会话检索上一轮凝练的经验（两会话） <!-- comet-task:2ffea3a5-2b66-4a77-a5de-d487e25d2176 -->
- [ ] 3.3 make check 全绿 + E2E S05 无回归 <!-- comet-task:a24dc71e-ecc8-413e-a33c-59907f9c43d0 -->

```

## docs/openspec/changes/agent-memory-system/.openspec.yaml

- Source: docs/openspec/changes/agent-memory-system/.openspec.yaml
- Lines: 1-2
- SHA256: 9cfa2ab963a8c9b58eecdb9fd5b55544e988fee8de8b887226ffc32d27744459

```md
schema: spec-driven
created: 2026-10-16

```

## docs/openspec/changes/agent-memory-system/specs/agent-memory-system/spec.md

- Source: docs/openspec/changes/agent-memory-system/specs/agent-memory-system/spec.md
- Lines: 1-50
- SHA256: 4f1892d215a5d383ee41e1e1fbb738c37ec794f318a26f8e3d953bca07fe30c8

```md
# agent-memory-system 规格草案

## Purpose

让 agent 拥有跨会话的可复用记忆：经验可记录、可检索、带溯源标注、防重复注入；与画像 memory.md（用户画像长期记忆）边界分明，互不污染。

## ADDED Requirements

### Requirement: 记忆记录与溯源

agent 可将可复用经验（用户偏好/红线/制作技巧/效果归因）记入记忆库；每条记忆带 origin_class（owner=用户明确陈述 / agent=agent 凝练 / system=系统事件）；一次性规格、临时参数、流水账不记录。

#### Scenario: 任务结束凝练经验
- **WHEN** 一轮任务结束且出现真正可复用的偏好/红线/技巧/归因
- **THEN** agent 给出拟记内容（1-3 条）并说明目标，用户确认后落库（origin=owner 或 agent）
- **THEN** 用户拒绝或未指定时不写入

#### Scenario: 不记一次性内容
- **WHEN** 内容为一次性规格、临时参数或流水账
- **THEN** 不写入记忆库

### Requirement: 记忆检索与注入标注

记忆检索工具返回结果带溯源标注（origin_class + 记录时间）；注入对话上下文的内容结构化标记，已注入过的内容不因相同检索而重复注入（recall-loop 预防）。

#### Scenario: 检索结果可溯源
- **WHEN** agent 检索记忆
- **THEN** 每条结果标注 origin_class 与创建时间

#### Scenario: 不重复注入
- **WHEN** 同一会话中相同记忆已被注入
- **THEN** 后续检索不重复返回该内容

### Requirement: compaction 前 flush

会话历史压缩（summarization）前，把当前会话的关键上下文写入 episodic 记录，防止压缩丢失可复用信息。

#### Scenario: 压缩前保存
- **WHEN** 会话触发历史压缩
- **THEN** 压缩执行前有关键上下文的 episodic 记忆落库

### Requirement: 与画像 memory.md 的边界

画像 memory.md 是用户画像的长期记忆（画像域）；agent 记忆库是运营经验记忆（agent 域）。两者互不写入对方；并行会话各自读所绑定画像的记忆，不跨画像借用。

#### Scenario: 边界不互写
- **WHEN** agent 记录经验
- **THEN** 写入 agent 记忆库，不修改任何画像的 memory.md（画像更新只经用户确认的画像管理流程）
- **WHEN** agent 读取画像
- **THEN** 只读当前会话绑定画像的 memory.md

```
