---
comet_change: agent-operating-contract
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-16-agent-operating-contract
status: final
---

# 设计：操作契约层

## 高层方案

```
SYSTEM_PROMPT（重构为契约层，agent_runtime.py）
  ├─ 人格段（SOUL 凝练：沟通风格+做成心态）
  ├─ 执行偏向 + Promised Work + ask-first 分级（静态规则，照 OpenClaw 语义中文化）
  ├─ 编排 glue 接线（manifest/calendar_ops/output_paths 一句话纪律）
  ├─ 五层索引（① 已有，保留）
  └─ 【技能目录】动态注入段（_skills_catalog() 渲染，带缓存）
        │ get_skills()（已有 TTL 缓存）按 layer 分组
        ▼
ops-* SKILL.md ×5（退化为路由层）
  ├─ ops-discover → skill-trending-topics / skill-trend-rider
  ├─ ops-plan     → skill-topic-evaluator
  ├─ ops-create   → copywriting + skill-quality-gate
  ├─ ops-publish  → skill-wechat-publisher（+ content_guard / persona_gate / publish-log 门）
  └─ ops-review   → skill-publish-analytics / skill-content-postmortem
```

## 关键决策

### D1：技能目录注入——复用 get_skills 而非自建
`get_skills()` 已带 300s TTL 缓存、已产出 name/description/layer。在 SYSTEM_PROMPT 组装处调用一次渲染为分组清单（只放 name+description 一句，不放全文）。119 个技能 × ~40 字 ≈ 5KB，提示词增量可接受；若后续技能数暴涨再加「只注入当前任务相关层」的过滤。

### D2：静态契约 vs 动态事实的边界
人格/执行偏向/follow-through/ask-first 是**静态规则**（照 OpenClaw「prompt 不预拒绝、风险下沉运行时」的精神中文化）；技能目录/画像列表是**动态事实**（每次组装时渲染）。缓存边界对齐：静态段在前（稳定前缀），动态段在后（易变后缀）——OpenClaw 的 provider 缓存边界工程的简化版，Python 侧无 prompt cache API 故只做顺序。

### D3：ops-* 路由层的引用方式
每个 ops-* SKILL.md 保留「触发条件+本层职责一句话+必读详细技能清单（路径）+本层特有约定」。详细流程一律在既有技能里改——**本次不改动 114 个既有技能的内容**，只修引用关系。ops-publish 例外：发布门三步（content_guard→persona_gate→publish-log）写进 ops-publish，因为既有 skill-wechat-publisher 不含这些门。

### D4：付费确认复用 ask_human
不新增确认机制。ask-first 规则要求 agent 在调用付费媒体能力前用 ask_human（已有 HITL 中断+卡片）给出范围+预估。费用预估数据源：无（OpenClaw 也无 pre-call 估算——它只有事后 usage）。agent 按媒体类型给出「将调用 N 次生图」这类可确认的范围描述即可，不编造单价。

### D5：manifest/calendar/output_paths 的接入深度
只做「提示词纪律+ops-* 路由层点名」，不改造脚本本身。这三个脚本已在 skills/shared/scripts/（随库复制而来），先验证可运行（烟测），不可用则在对应 ops 技能里标注。

## 风险与对策

- **风险**：提示词膨胀导致指令遵循度下降 → 对策：静态段控制在 ~60 行内；技能目录只放 name+description；实施后用探针验证路由命中率
- **风险**：人格段与江小湖画像风格混淆 → 对策：人格段管 agent 沟通风格，明确写「内容风格以画像为准」
- **风险**：persona_gate/publish-log 脚本在库里但可能对不上我们的数据格式 → 对策：D5 烟测先行，不通则降级为「流程约定」并在 ops-publish 标注

## Open Questions

无（batch 决策已由用户确认：完整对齐、按需开启）。
