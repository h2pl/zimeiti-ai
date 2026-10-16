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
