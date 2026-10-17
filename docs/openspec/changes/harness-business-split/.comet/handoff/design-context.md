# Comet Design Handoff

- Change: harness-business-split
- Phase: design
- Mode: compact
- Context hash: 0462b6f0da7fc26a46d338d515f7448644c2d28dda278b5293bd76395d0e4c97

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/harness-business-split/proposal.md

- Source: docs/openspec/changes/harness-business-split/proposal.md
- Lines: 1-58
- SHA256: 9a98d7d96a57a6f6fc194f3a4685cad4bd3ff6d6643f3e130db48ffe02f484cf

```md
---
comet_change: harness-business-split
---

# harness-business-split：agent harness 与业务代码分层

## Why

依赖测绘（grep 级）显示后端已接近单向依赖，但 harness 与业务仍有真实耦合：

- **harness → business**：3 个文件 7 个符号——`agent_runtime._skills_catalog`
  函数级引 `content.skills.get_skills`；`runtime/chat.py` 模块级引 `content`
  私有符号（`_persona_prefix`/`find_skill`/`_attachment_*`）；`runtime/status.py`
  引 `list_personas`/`get_skills`
- **business → harness**：`automations/scheduler.py` 函数级硬引 `ask_sync`
  （personas 已 DI 化，scheduler 没有）
- **结构错位**：`runtime/chat.py`、`runtime/status.py` 实为 API 路由却住在
  runtime/ 里，让人误以为路由属于 harness
- 后果：改业务（技能目录、画像、附件）要动 harness 装配代码；harness 无法
  独立测试/复用；分层规则只存在于直觉里，没有任何机制守卫

## What Changes

- **新建兄弟包 `zimeiti_harness`**（与 `zimeiti_api` 平级，同 venv）：
  `runtime/`（agent_runtime、model_fallback、exec_tool、pricing、schemas、
  status.py/chai.py 除外）+ `memory/` + `usage.py`
- **依赖倒置**：`zimeiti_harness/contract.py` 定义注入点——技能目录 provider
  由组装层（app.py）注册，harness 不再知道 content 的存在
- **路由归位**：`runtime/chat.py`→`zimeiti_api/chat_router.py`、
  `runtime/status.py`→`zimeiti_api/status_router.py`（对齐 `usage_router.py` 既有惯例）
- **scheduler DI**：`set_ask_sync(fn)` setter，app.py 接线（对齐 personas 范式），
  删除函数级硬 import
- **分层守卫**：确定性测试扫描 `zimeiti_harness/` 源码，assert 无业务域 import
  （允许 `zimeiti_api.core` 共享 infra），随 make check 防回潮
- **配置面**：pyproject packages / mypy / ruff / bandit / Makefile 覆盖率范围同步

## Non-Goals

- **core/ 不动**：paths/pg/settings/timeouts 是共享 infra（无业务逻辑），harness
  允许 import——本次分的是 harness 与业务，不是 harness 与地基
- **core/pg.py 表 schema 混装**（messages/pending/checkpoint 与业务表同文件）：
  记为已知不完美，拆表属于独立变更（牵动迁移，本轮不动）
- **exec_tool 注册表硬编码脚本路径**：数据耦合非 import 耦合，维持现状
- 提示词契约里的业务文案（`_CONTRACT_HEAD`）：文案更新走 contract 文档，
  抽取成配置属过度设计，不动

## Capabilities

### New Capabilities

- `harness-business-split`：harness 与业务代码分属两个包，harness 对业务域的
  import 为零且有确定性测试守卫；业务对 harness 的调用走显式注入点

## Impact

新增 `zimeiti_harness` 包；`zimeiti_api` 内 13 个文件的 import 更新（4 源码 +
9 测试）；app.py 组装点接线；Makefile/pyproject 检查范围更新。运行行为零变化
（纯结构重构），由全量测试 + E2E + 探针证明。

```

## docs/openspec/changes/harness-business-split/design.md

- Source: docs/openspec/changes/harness-business-split/design.md
- Lines: 1-86
- SHA256: 8b416c855efd162cc19d6f2323e0c8b14df7574c2a96d4f0d7342e0b26419fb0

[TRUNCATED]

```md
---
comet_change: harness-business-split
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：harness/business 分层

## 目标结构

```
apps/api/
  zimeiti_harness/            # agent harness——禁止 import 业务域
    __init__.py
    contract.py               # 注入点（见 D1）
    runtime/
      agent_runtime.py        # 改：_skills_catalog 走 contract；其余不动
      model_fallback.py  exec_tool.py  pricing.py  schemas.py   # 原样搬
      __init__.py             # 薄出口：ask_sync/chat_structured/build_system_prompt/set_main_loop
    memory/                   # store/tools/flush 原样搬
    usage.py                  # 原样搬
  zimeiti_api/                # 业务 + 组装
    chat_router.py            # ← runtime/chat.py（/api/chat/stream 路由）
    status_router.py          # ← runtime/status.py（/api/status 路由）
    usage_router.py           # 原地（import 改指向 harness）
    content/ automations/ platforms/ operations/ governance/ core/
    app.py                    # 组装层：唯一接线点
```

## 关键决策

### D1：contract.py 注入点（依赖倒置），不是回调地图散落各处

harness 需要的业务输入只有一类：**提示词装配期的目录数据**（技能清单）。
集中到一个 contract 模块：

```python
# zimeiti_harness/contract.py
_skills_provider: Callable[[], list] = lambda: []
def register_skills_provider(fn: Callable[[], list]) -> None: ...
def skills_catalog() -> list:  # 供 agent_runtime._skills_catalog 渲染
    try: return _skills_provider()
    except Exception: return []
```

app.py 启动时 `harness.contract.register_skills_provider(content.skills.get_skills)`。
画像前缀不进 contract——`chat.py` 归位为 `chat_router.py` 后**留在业务侧**，
它直接 import content 是合法的（业务→harness 单向，路由属于业务组装）。

### D2：chat.py/status.py 归位为路由而非搬进 harness

它们 95% 是 FastAPI 路由（SSE 流、请求模型、附件解析），只有最后一步调
harness 的 ask/harness 流式入口。路由属于业务组装层——搬到 `zimeiti_api/`
顶层（对齐既有 `usage_router.py` 命名惯例），harness 保持「无 HTTP」。

### D3：scheduler 走 setter 注入（对齐 personas 范式）

`automations/scheduler.py` 加 `set_ask_sync(fn)`；app.py lifespan 里
`automations.scheduler.set_ask_sync(harness_runtime.ask_sync)`。守卫规则：
scheduler 源码不得出现 agent 入口的 import。

### D4：core/ 定性为共享 infra，划在「完全分开」边界之外

paths/pg/settings/timeouts 无业务逻辑，harness 依赖它们如同依赖 stdlib。
把 core 抽成第三个包是概念洁癖，churn 巨大且收益为零——明确写入 Non-Goal。
守卫规则相应表述为：harness 禁止 import `zimeiti_api.{content,automations,
platforms,operations,governance,routers}`，`zimeiti_api.core` 白名单放行。

### D5：import 更新策略——一次到位，不留 shim

13 个文件直接改 import（`zimeiti_api.runtime` → `zimeiti_harness.runtime`），
**不留 re-export shim**——shim 会让分层守卫形同虚设。测试文件一并更新。

## 风险与对策

- **风险**：myopic 遗漏某个延迟 import → 分层守卫扫描的是源码文本，能抓到
  字符串级 import；`make check` + E2E 兜底运行时
- **风险**：pyproject/mypy/ruff/bandit/Makefile 检查范围漏配 harness → 各处
  scope 显式更新并在验证清单核对（mypy 报 0 文件即漏配信号）

```

Full source: docs/openspec/changes/harness-business-split/design.md

## docs/openspec/changes/harness-business-split/tasks.md

- Source: docs/openspec/changes/harness-business-split/tasks.md
- Lines: 1-22
- SHA256: b43626bbafffa4fd68d1dd66d4b6414bb693fa09cd5fbed92a950e7f4b633c3c

```md
---
comet_change: harness-business-split
---

# Tasks：harness/business 分层

## 1. 包落位与依赖倒置

- [ ] 1.1 建 `zimeiti_harness/`：git mv runtime 五模块 + memory/ + usage.py；contract.py 注入点 <!-- comet-task:e281761b-f2a2-4763-b469-83df3408076a -->
- [ ] 1.2 agent_runtime._skills_catalog 改走 contract；删 content import <!-- comet-task:159be7ae-7493-4ff6-bf6f-eb24bc1f3d9c -->
- [ ] 1.3 chat.py/status.py 归位 zimeiti_api/chat_router.py、status_router.py；app.py 更新 <!-- comet-task:7a042994-ee11-4c91-87ae-ce17130c6e53 -->

## 2. 注入与守卫

- [ ] 2.1 scheduler set_ask_sync 注入；删函数级硬 import；app.py 接线 <!-- comet-task:a3ad1618-d8bb-458c-b0d9-ba5575e41724 -->
- [ ] 2.2 分层守卫确定性测试（扫描 harness 源码禁业务域 import，core 白名单） <!-- comet-task:f5b20336-9ead-4da4-b58e-2da55c24114c -->
- [ ] 2.3 pyproject/mypy/ruff/bandit/Makefile 范围同步；全库 import 更新（13 文件） <!-- comet-task:28c2fda5-d03d-4fe9-bd2e-e9446256d596 -->

## 3. 验证

- [ ] 3.1 make check 全绿 + 分层守卫在册；make evals 5/5 <!-- comet-task:8c685111-1104-46c6-99d6-6f87b3fc3e65 -->
- [ ] 3.2 E2E 全量 63/63；对话/结构化/自动化探针行为一致 <!-- comet-task:a1d4f40a-b2ad-45a1-b9d9-2a461c3068e4 -->

```

## docs/openspec/changes/harness-business-split/.openspec.yaml

- Source: docs/openspec/changes/harness-business-split/.openspec.yaml
- Lines: 1-2
- SHA256: 4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9

```md
schema: spec-driven
created: 2026-10-17

```

## docs/openspec/changes/harness-business-split/specs/harness-business-split/spec.md

- Source: docs/openspec/changes/harness-business-split/specs/harness-business-split/spec.md
- Lines: 1-45
- SHA256: e96cb31dc88cc10d2fad755b5f12adca9097887aa0d646c49b817069c10194d0

```md
# harness-business-split 规格草案

## Purpose

agent harness 与业务代码分属两个包，依赖单向可由测试机械验证，业务对 harness
的调用只经显式注入点。

## ADDED Requirements

### Requirement: harness 包与业务包物理分离

系统 SHALL 包含与 `zimeiti_api` 平级的 `zimeiti_harness` 包，承载 agent 装配、
模型 fallback、exec 工具、记忆、用量、结构化 schema；业务域（content/automations/
platforms/operations）与 API 路由 MUST 留在 `zimeiti_api`。

#### Scenario: 包结构落位
- **WHEN** 检查仓库结构
- **THEN** `zimeiti_harness/` 含 runtime/memory/usage 与 contract 注入点，
  `zimeiti_api/runtime/` 不再存在，路由在 `zimeiti_api/chat_router.py` 等

### Requirement: harness 对业务域零 import 且有守卫

`zimeiti_harness` 源码 MUST NOT import 业务域（content/automations/platforms/
operations/governance 及其符号）；允许 import 共享 infra `zimeiti_api.core`。
确定性测试 SHALL 扫描 harness 源码并断言零违规，随 make check 运行。

#### Scenario: 守卫测试拦截回潮
- **WHEN** 任何人向 `zimeiti_harness/` 内的文件加入 `from zimeiti_api.content...`
- **THEN** `make check` 的分层守卫测试失败并指出违规文件与行

### Requirement: 业务对 harness 只经注入点

业务模块 MUST NOT 硬 import harness 的 agent 入口；需要 agent 能力的模块
（如 automations scheduler）SHALL 通过组装层注入的 setter 获得入口
（对齐 personas 的 set_enhance_runtime 范式）。

#### Scenario: scheduler 经注入获得 ask_sync
- **WHEN** 定时任务执行 prompt 类型任务
- **THEN** ask_sync 来自组装层注入的 setter，scheduler 源码无
  `from ..runtime.../from zimeiti_harness...` 的 agent 入口 import

### Requirement: 行为零变化

本次为纯结构重构：全量测试、E2E、行为探针结果 MUST 与重构前一致
（229 单测 / E2E 63 项 / 探针 PASS）。

```
