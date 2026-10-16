---
comet_change: agent-memory-system
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-16-agent-memory-system
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
