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
