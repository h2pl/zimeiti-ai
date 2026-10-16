# Comet Design Handoff

- Change: agent-behavior-evals
- Phase: design
- Mode: compact
- Context hash: 111456bb8aa1ab2ffafb46c91ff74b298999389dc58fb20ec3591b8b9a5897e0

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/agent-behavior-evals/proposal.md

- Source: docs/openspec/changes/agent-behavior-evals/proposal.md
- Lines: 1-34
- SHA256: bd08e625a6f65f573cb955aa3d5950cdd049be1e21ab1206c5063c18649d9b0b

```md
---
comet_change: agent-behavior-evals
---

# agent-behavior-evals：agent 行为回归套件

## Why

六个变更（五层流程 / 命令执行 / 前端债 / 操作契约 / 记忆 / 韧性）的行为结论**全部靠手工探针验证，跑完即焚**——每次我起测试服务、发一条真实 LLM 请求、肉眼判断「路由命中了吗 / 付费确认了吗 / 记忆跨会话了吗」，然后清理数据。证据留在验证报告里，**没有任何可重复执行的断言**。

后果是：下次谁改一句 SYSTEM_PROMPT、加一个工具、调一次技能目录注入，没人能证明行为有没有退化。单测覆盖的是函数（exec 白名单、记忆存储、fallback 判定），覆盖不到「agent 面对真实任务时的实际行为」；UI E2E 覆盖的是界面，不是 agent 决策。这中间有一层**行为回归的真空**。

实证：当前 `create_deep_agent(` 未传 `subagents`/`response_format`，工具清单来自 `_build_tools()`——任何一处改动都会改变行为，而现在没有任何自动化能捕获这种改变。

## What Changes

- 新增 `apps/api/tests/evals/`（行为回归套件，与单测分离）：
  - **确定性层**（无 LLM，可进 `make check`）：工具可发现性（技能目录含目标技能）、契约段在位（执行偏向/follow-through/ask-first/记忆节）、白名单拒绝、fallback 判定矩阵——这些都是纯函数断言，秒级
  - **行为层**（真实 LLM，`make evals` 单独跑，需 OPENAI_API_KEY）：把五个手工探针脚本化成断言——① 选题评估路由到详细技能；② 付费操作触发 ask_human；③ 清晰可逆任务直执行不提问；④ 跨会话记忆检索命中并带溯源；⑤ 主模型坏端点时自动切换且完成回复
- `Makefile` 加 `evals` 目标（起独立端口实例 → 跑行为层 → 清理演示数据 → 退出码即结果）；无 API key 时明确 SKIP 而非失败
- 行为层断言用「关键词命中 + 工具调用轨迹」双证据，避免脆弱的字面量断言；每条用例输出耗时与证据摘要，便于人工复核

## Capabilities

### New Capabilities

- `agent-behavior-evals`：agent 行为可重复回归——确定性层随门禁跑，行为层一条命令跑完并给出通过/失败与证据

## Non-Goals

- 替代单测或 UI E2E（三者分层，互不覆盖）
- 离线桩模型的全量行为仿真（桩模型的"通过"不代表真模型行为，价值有限）
- 打分式评测（LLM-as-judge）——先用确定性断言，judge 留后续
- 性能/延迟基线

```

## docs/openspec/changes/agent-behavior-evals/design.md

- Source: docs/openspec/changes/agent-behavior-evals/design.md
- Lines: 1-54
- SHA256: d50616b738c64641baf5ad4fde6090f05b3e5b9012b77bda4d1236fa52d84561

```md
---
comet_change: agent-behavior-evals
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：agent 行为回归套件

## 高层方案

```
apps/api/tests/evals/
  ├─ conftest.py        端口/实例管理（起独立 8121 实例，用例级清理）
  ├─ test_deterministic.py   ← 进 make check（无 LLM，秒级）
  │     契约段在位 / 技能目录含详细技能 / 白名单拒绝 / fallback 判定矩阵
  └─ test_behavior.py        ← 仅 make evals（真实 LLM，分钟级）
        5 条用例：路由 / 付费确认 / 可逆直做 / 跨会话记忆 / fallback 切换

Makefile: evals 目标（uv run pytest tests/evals -m behavior）
标记：@pytest.mark.behavior；make check 跑 tests/ 但用 -m "not behavior" 排除
```

## 关键决策

### D1：两层分离，行为层不进 make check
行为层要真实 LLM（每条 10-60s，五条数分钟，且花钱）。塞进 `make check` 会让本地门禁不可用。故：
- 确定性层（`tests/evals/test_deterministic.py`）：随 `make check` 跑
- 行为层（`tests/evals/test_behavior.py`，标 `behavior`）：`make evals` 触发；pytest 默认收集时用 `-m "not behavior"` 排除（写进 Makefile check 目标与 pytest 配置）

### D2：断言用双证据，不用字面量
手工探针时代我判「提到 topic-evaluator 就算命中」——太脆。改为：
- **工具轨迹证据**：从 SSE 的 `activity` 事件与最终消息里提取工具调用名（如 read_file / exec_script / memory_search / ask_human）
- **语义证据**：回复关键词命中（多条同义表述任一即可）
两条都有才算通过；只有一条 → 报「证据不足」并打印原文片段供人工复核。

### D3：行为层自带实例与清理，不依赖外部服务
每个 session 起独立端口（8121），用例结束删会话/清记忆条目/清 automation 与 usage 记录。用例失败也要清理（`finally`）。

### D4：fallback 用例的环境构造
主模型指向 `http://127.0.0.1:<空闲端口>/v1`（必连不上），备用写 `deepseek-chat@https://api.deepseek.com`——复用 `.env` 的真实 key。断言：① 服务日志出现切换记录；② 回复非空且不含「未配置模型」。

### D5：超时与费用护栏
行为层单条上限 300s；套件总耗时上限 ~10min。付费确认用例**只要求触发 ask_human**，不实际执行付费调用（避免真花钱）。

## 风险与对策

- **风险**：真实 LLM 输出不稳定导致偶发失败 → 对策：双证据降低脆弱性；失败时打印完整回复尾部 500 字；不重试掩盖问题
- **风险**：行为层污染真实数据（记忆/内容库）→ 对策：D3 清理 + 用例用独立 sessionKey 前缀 `eval-`
- **风险**：确定性层断言过严阻碍正常改动 → 契约段断言只查小节标题存在，不查措辞

## Open Questions

无。

```

## docs/openspec/changes/agent-behavior-evals/tasks.md

- Source: docs/openspec/changes/agent-behavior-evals/tasks.md
- Lines: 1-26
- SHA256: 670d35ff6d5ad1f89e7c478c709c7e8340a621e5a320be92244ec946f4870499

```md
---
comet_change: agent-behavior-evals
---

# Tasks：agent 行为回归套件

## 1. 确定性层（进 make check）

- [ ] 1.1 `tests/evals/` 骨架 + conftest（端口/实例管理、用例清理、behavior 标记约定） <!-- comet-task:e511638b-55f0-43ac-bf54-529d1fe116c1 -->
- [ ] 1.2 契约段在位断言（执行偏向 / follow-through / ask-first / 记忆 / 五层索引 / 技能目录） <!-- comet-task:8435f1d9-0e9f-4802-8501-a26209014d06 -->
- [ ] 1.3 技能目录含既有详细技能断言（skill-topic-evaluator 等）+ 工具装配断言（exec_script / memory_* / ask_human 在册） <!-- comet-task:fcbd4ba7-1417-4b80-939e-60bd7e6ab9a0 -->
- [ ] 1.4 白名单拒绝 + fallback 判定矩阵断言（复用既有逻辑，补 4xx/5xx/429/连接错误四类） <!-- comet-task:fee480a9-d726-4bc4-8247-e5d0e3be3ec3 -->

## 2. 行为层（make evals，真实 LLM）

- [ ] 2.1 用例①：选题评估 → 路由到详细技能（工具轨迹含 read_file 命中 SKILL.md + 回复含评估结论） <!-- comet-task:b3d5dc20-b475-4f17-bbfa-7f181bf2c4d2 -->
- [ ] 2.2 用例②：付费生图 → 触发 ask_human 且不实际执行（双证据） <!-- comet-task:cb3e344a-7633-40e6-a88d-27af01773882 -->
- [ ] 2.3 用例③：清晰可逆任务 → 直执行不提问 <!-- comet-task:3348d410-0112-48b6-9740-498307797e3b -->
- [ ] 2.4 用例④：跨会话记忆 → 会话A 记录、会话B 检索命中并带溯源 <!-- comet-task:10a14805-ffd9-4fae-8216-2dfbee4dabf0 -->
- [ ] 2.5 用例⑤：fallback 切换 → 主模型坏端点，日志出现切换且回复正常 <!-- comet-task:8eae5e0a-f29f-422a-a820-ad16e30114dc -->
- [ ] 2.6 无密钥时整体 SKIP（退出码 0）+ 演示数据清理（finally） <!-- comet-task:553489fa-5c1a-4c6e-9469-4c0be29899a0 -->

## 3. 门禁接线

- [ ] 3.1 Makefile `evals` 目标；`check` 目标排除 behavior 标记 <!-- comet-task:a8f284df-20e4-4164-8491-cc2fe97cf397 -->
- [ ] 3.2 跑通：`make check`（含确定性层）+ `make evals`（五条全绿）双验 <!-- comet-task:60808f23-59c8-4af3-9b43-27825d529ea2 -->

```

## docs/openspec/changes/agent-behavior-evals/.openspec.yaml

- Source: docs/openspec/changes/agent-behavior-evals/.openspec.yaml
- Lines: 1-2
- SHA256: 4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9

```md
schema: spec-driven
created: 2026-10-17

```

## docs/openspec/changes/agent-behavior-evals/specs/agent-behavior-evals/spec.md

- Source: docs/openspec/changes/agent-behavior-evals/specs/agent-behavior-evals/spec.md
- Lines: 1-39
- SHA256: 64c6fe88f467de8af37eaf8571f8d437f366f9e3bd7fdd6ccb8357eb3ba2539f

```md
# agent-behavior-evals 规格草案

## Purpose

让 agent 的行为结论可重复验证：确定性层随门禁跑（改动提示词/工具装配即刻报错），行为层一条命令跑完真实 LLM 探针并给出证据；无密钥时明确跳过而非失败。

## ADDED Requirements

### Requirement: 确定性行为断言随门禁执行

无需 LLM 的行为前提可被自动断言：技能目录包含目标技能、契约段各小节在位、白名单外脚本被拒、fallback 判定矩阵正确。这些断言进入 `make check`，秒级完成。

#### Scenario: 契约段缺失即失败
- **WHEN** SYSTEM_PROMPT 缺少执行偏向/follow-through/ask-first/记忆任一节
- **THEN** 确定性层断言失败，`make check` 报红

#### Scenario: 技能目录不含目标技能即失败
- **WHEN** 技能目录注入结果不含既有详细技能（如 skill-topic-evaluator）
- **THEN** 断言失败

### Requirement: 行为层探针可一键复跑

`make evals` 起独立端口实例，依次跑五个行为用例，每条输出证据摘要与耗时，退出码反映整体结果；用例间清理演示数据。

#### Scenario: 五条用例全部可复跑
- **WHEN** 配置 OPENAI_API_KEY 后执行 `make evals`
- **THEN** 选题评估路由 / 付费确认 / 可逆直执行 / 跨会话记忆 / fallback 切换 五条用例依次执行并各自给出通过与否与证据

#### Scenario: 无密钥时明确跳过
- **WHEN** 未配置 OPENAI_API_KEY
- **THEN** 行为层整体 SKIP（退出码 0），并打印「未配置模型密钥，跳过行为层」

### Requirement: 断言基于证据而非字面量

行为断言用「工具调用轨迹 + 关键词命中」双证据；单条证据不足时不通过，避免脆弱断言与假阳性。

#### Scenario: 付费确认用例的判据
- **WHEN** 用户要求执行付费媒体生成
- **THEN** 判据为「触发 ask_human 事件」且「回复含费用/确认/范围相关表述」，两者缺一不通过

```
