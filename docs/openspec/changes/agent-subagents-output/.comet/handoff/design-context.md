# Comet Design Handoff

- Change: agent-subagents-output
- Phase: design
- Mode: compact
- Context hash: bdbd92dd07ff6050a1fb0b38a83aa34227080272844e662c0b08f5a75e050509

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/agent-subagents-output/proposal.md

- Source: docs/openspec/changes/agent-subagents-output/proposal.md
- Lines: 1-44
- SHA256: 0c81c80b9fae3cf601ce4c80156c30310ea513d7c95d626f6a5542501ae908bb

```md
---
comet_change: agent-subagents-output
---

# agent-subagents-output：专属子代理与结构化输出

## Why

对照 OpenClaw 源码（`docs/tools/subagents.md`）：它用 `sessions_spawn` 派生子会话，
支持 `context: "fork"` 继承父 transcript、默认不给 session/message 工具、可配嵌套深度，
且**子 agent 可用更便宜的模型**（`agents.defaults.subagents.model`）。

我们实证：`_build_agent` 调 `create_deep_agent(` 时**未传 `subagents` 也未传
`response_format`**——只有 deepagents 默认的通用子代理（吃主模型 token，无角色约束），
结构化产出（如选题评估的评分表）只能靠提示词约束 JSON，偶发不合规。

具体代价：
- 探索类子任务（读技能库、扫内容库、grep 历史产物）与主推理同价，长任务成本高
- 子 agent 没有角色边界（通用子代理可能自作主张写文件）
- 结构化产出不稳定：选题评估的「七维评分+结论」靠提示词约束，格式偶发漂移

## What Changes

- `_build_agent` 传 `subagents`：定义两个专属子代理
  - `research`：只读探索（ls/glob/grep/read_file），**便宜模型**（`ZIMEITI_SUBAGENT_MODEL`，缺省则用主模型），系统提示词限定「只查不写，回报事实与路径」
  - `draft`：写作子代理（写 outputs/），与主模型同档，限定「写完回报路径与字数，不做发布动作」
  - 两者均不给 `ask_human` / `exec_script`（避免子代理越权提问与跑脚本）
- 结构化输出：为「选题评估」场景接 `response_format`（Pydantic 模型：七维评分+结论+建议），
  经 `/api/chat` 的结构化请求路径可选开启；默认不影响普通对话
- 环境变量可配：`ZIMEITI_SUBAGENT_MODEL`（子代理模型，缺省=主模型）、`ZIMEITI_SUBAGENT_ENABLED`

## Capabilities

### New Capabilities

- `specialized-subagents`：主 agent 可按角色派生只读探索/写作子代理，子代理可用便宜模型、工具面受限
- `structured-output`：结构化请求可要求 agent 按 schema 产出（首个场景：选题评估评分表）

## Non-Goals

- 并行 swarm / fan-out collectors（OpenClaw Code Mode 能力，本地单用户暂不需要）
- 自定义中间件（Summarization 等仍用默认）
- 前端结构化渲染（本次只保证产出合规，UI 渲染后续）
- 子代理嵌套深度策略（默认单层足够）

```

## docs/openspec/changes/agent-subagents-output/design.md

- Source: docs/openspec/changes/agent-subagents-output/design.md
- Lines: 1-53
- SHA256: 1a8e6e391f5941ee4f18c680d6e6384ea316edbe9ec86ba9fbb5f8be5aa81de7

```md
---
comet_change: agent-subagents-output
role: technical-design
canonical_spec: openspec
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

```

## docs/openspec/changes/agent-subagents-output/tasks.md

- Source: docs/openspec/changes/agent-subagents-output/tasks.md
- Lines: 1-22
- SHA256: d6effeca3df106d896fc0afcb4d395a61aa27d81df7f78890d1faea4ffa70b48

```md
---
comet_change: agent-subagents-output
---

# Tasks：专属子代理与结构化输出

## 1. 子代理定义与装配

- [ ] 1.1 `_build_subagents()`：research（只读工具+`ZIMEITI_SUBAGENT_MODEL`）+ draft（写工具、无 ask_human/exec_script）；`ZIMEITI_SUBAGENT_ENABLED` 可关 <!-- comet-task:1620439c-b5d7-434b-bb81-ea9a263d0f85 -->
- [ ] 1.2 `_build_agent` 传入 subagents；子代理 prompt 写明回报契约（只查不写 / 写完报路径字数不发布） <!-- comet-task:e53bc1c6-8b8d-40ab-903a-fb6e3ecd0793 -->
- [ ] 1.3 单测：子代理工具面不含禁用工具；开关生效；未设子代理模型时不传 model 字段 <!-- comet-task:19fafd30-bd0f-4241-a039-ab9532be9cc5 -->

## 2. 结构化输出

- [ ] 2.1 `runtime/schemas.py`：TopicEvaluation（维度分/综合结论/建议） <!-- comet-task:a364631c-ede7-4e70-9997-38a443a319f8 -->
- [ ] 2.2 `chat_structured()` 轻量入口：按 schema 建临时 graph（进程内缓存），不污染主对话 <!-- comet-task:2d3371b9-6452-42ff-a11c-c1ad5c7bbc73 -->
- [ ] 2.3 单测：schema 字段与类型约束；未启用结构化时主对话行为不变 <!-- comet-task:b611f39f-db5e-45e6-a198-dadb743020c5 -->

## 3. 验证

- [ ] 3.1 确定性断言补：子代理在册且工具面符合约束（并入 evals 确定性层） <!-- comet-task:acf155c2-bf3d-430f-9b43-5cc4c4a5912a -->
- [ ] 3.2 make check + make evals 双绿；探针：探索类任务确实派了 research 子代理 <!-- comet-task:3427f8ef-2b18-4a63-a4c9-61368b9165be -->

```

## docs/openspec/changes/agent-subagents-output/.openspec.yaml

- Source: docs/openspec/changes/agent-subagents-output/.openspec.yaml
- Lines: 1-2
- SHA256: 4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9

```md
schema: spec-driven
created: 2026-10-17

```

## docs/openspec/changes/agent-subagents-output/specs/agent-subagents-output/spec.md

- Source: docs/openspec/changes/agent-subagents-output/specs/agent-subagents-output/spec.md
- Lines: 1-36
- SHA256: fc64747e2927ec70a834a4ef9629f4862a1e69e0ed9c49f81c11379267311efc

```md
# agent-subagents-output 规格草案

## Purpose

让子代理有角色边界与成本分层，让结构化产出有 schema 约束：探索类子任务可用便宜模型且只读，写作子代理限定产出范围；结构化请求可按 schema 产出（首个场景：选题评估评分表）。

## ADDED Requirements

### Requirement: 专属子代理可按角色派生

主 agent 可派生「只读探索」与「写作」两种角色子代理；只读子代理不得具备写文件工具，写作子代理不得具备提问与脚本执行工具；子代理模型可独立配置（缺省同主模型）。

#### Scenario: 探索类子任务用只读子代理
- **WHEN** 主 agent 需要大范围检索技能库/内容库/历史产物
- **THEN** 派 `research` 子代理完成；该子代理工具面只含只读工具，回报事实与路径
- **THEN** 若配置了 `ZIMEITI_SUBAGENT_MODEL`，该子代理用便宜模型而非主模型

#### Scenario: 子代理不得越权
- **WHEN** 子代理被派生
- **THEN** 它拿不到 ask_human（不打断用户）与 exec_script（不跑脚本）；只读子代理拿不到写工具

#### Scenario: 可关闭
- **WHEN** 设置 `ZIMEITI_SUBAGENT_ENABLED=false`
- **THEN** 退回 deepagents 默认通用子代理行为

### Requirement: 结构化输出按 schema 产出

结构化请求可指定 schema，agent 按 schema 产出结构化结果；首个落地场景为选题评估评分表（维度分+综合结论+建议）。

#### Scenario: 选题评估结构化产出
- **WHEN** 以结构化方式请求选题评估
- **THEN** 返回符合 schema 的结果（各维度分数、综合结论、建议要点），字段齐全且类型正确

#### Scenario: 不影响普通对话
- **WHEN** 普通对话未指定 schema
- **THEN** 行为与之前一致（不强制结构化）

```
