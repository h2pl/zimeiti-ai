---
comet_change: agent-subagents-output
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-17-agent-subagents-output
status: final
---

# 设计：专属子代理与结构化输出

## 高层方案

```
_build_agent()
  ├─ subagents=[research, draft]        ← 新增（ZIMEITI_SUBAGENT_ENABLED 可关）
  │     research: 只读工具 + ZIMEITI_SUBAGENT_MODEL（便宜）+ 「只查不写」prompt
  │     draft:    写工具（outputs/**）+ 主模型 + 「写完报路径字数，不发布」prompt
  │     两者均不含 ask_human / exec_script
  └─ response_format=None（默认）  ← 结构化请求场景由调用方传入 schema

zimeiti_api/runtime/schemas.py（新增）
  └─ TopicEvaluation（维度分 dict + 综合结论 + 建议 list）— 首个结构化场景
```

## 关键决策

### D1：子代理工具面按角色裁剪（用 deepagents 的 SubAgent 字段）
`SubAgent` 支持 `tools` / `model` / `skills` / `permissions` 独立配置（`middleware/subagents.py:84-140`）。
- research：只给只读工具（ls/glob/grep/read_file）——不传 write/edit，天然无写能力
- draft：给 write/edit，但不给 ask_human/exec_script
- 两者都不传 `interrupt_on`，子代理永不中断用户

### D2：便宜模型走环境变量，缺省同主模型
`ZIMEITI_SUBAGENT_MODEL` 未设时**不传 model 字段**（继承主模型），避免"配了个不存在的模型导致子代理全挂"。设了才用——且沿用 `_mk` 的 `模型名@base_url` 解析，与主链一致。

### D3：response_format 只在显式请求时启用
`create_deep_agent` 的 `response_format` 是**图级**配置，一旦设了会影响所有输出。故主 agent 不设；
结构化场景另建一个轻量入口（`chat_structured`）：用同一 backend/permissions 建一个临时
graph 并带 schema——不污染主对话。首版只落地选题评估一个 schema，验证价值后再扩。

### D4：子代理不继承 fork 上下文
deepagents 的 `mode="fork"` 标为 experimental（源码注释明说可能变）。默认隔离子代理只收
任务描述——这正好符合我们的用途（探索任务自带上下文即可），故不用 fork。

## 风险与对策

- **风险**：便宜模型子代理能力不足导致探索质量下降 → 对策：默认不设（同主模型），
  设了才降档；research 的 prompt 强调「回报事实与路径，不做判断」
- **风险**：结构化 graph 与主 graph 双份构建成本 → 对策：进程内缓存（同 `_AGENT` 单例思路），按 schema 名缓存
- **风险**：子代理写了不该写的文件 → 对策：draft 子代理同样受 backend permissions 约束（outputs/** 才可写）

## Open Questions

无。
