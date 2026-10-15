# Comet Design Handoff

- Change: browser-e2e
- Phase: design
- Mode: compact
- Context hash: c14ca6bbc02d411ad714cd828031b038e2a66439da817d33a371b3a10143eb3a

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/browser-e2e/proposal.md

- Source: docs/openspec/changes/browser-e2e/proposal.md
- Lines: 1-27
- SHA256: 6d1f794944eaf40997cd3133e718b9c24a3b66e7b20b89c482eb396ed5361ad4

```md
# Proposal: browser-e2e

## Why

浏览器级 E2E 目前是单个 300 行脚本（`apps/scripts/browser_e2e.py`），仅覆盖 5 个粗粒度场景（首屏/导航/选题/对话/渲染）。用户路径远不止这些：排期、内容库预览、画像向导、账号、设置、热点跳转等全部没有浏览器层覆盖；单文件结构也无法承载"覆盖每个用户路径"的目标。另外 LLM 调用走真实 `.env` key，慢且不确定——需要 mock 边界让全链路测试确定性化。

## What Changes

- 新建 `apps/e2e/` 独立目录管理浏览器自动化测试：
  - `runner.py`——双端目标管理（spawn zimeiti:8110 / Easel:7860、就绪等待、teardown）
  - `mock_llm.py`——OpenAI 兼容流式 mock 服务器（本地端口，zimeiti 后端以 `OPENAI_BASE_URL` 指向它），对话/画像向导走真实后端链路但 LLM 响应确定性
  - `helpers.py`——导航点击、欢迎弹层处理、网络回包同步原语、数据清扫
  - `parity.py`——双端观测值对齐比较器
  - `scenarios/`——按用户路径拆分的场景模块（每路径一文件）
- 场景覆盖（每个用户路径）：首屏引导、全页面导航、选题 CRUD、选题→排期→日历、对话流式（含新建会话/删除会话）、内容库浏览+文件预览、画像列表+创建向导+删除、账号页 whoami、设置面板模型通道、热点→做内容跳转
- 删除 `apps/scripts/browser_e2e.py`（内容全部迁移重组，无行为丢失）
- `make e2e-browser` 指向新入口；套件可单跑某场景、可单端跑（调试用）

## Capabilities

### New Capabilities

- `browser-e2e-suite`: 浏览器级双端对齐测试套件的结构、场景覆盖与运行契约

### Modified Capabilities

（无——本变更只新增测试设施，不改产品行为）

```

## docs/openspec/changes/browser-e2e/design.md

- Source: docs/openspec/changes/browser-e2e/design.md
- Lines: 1-64
- SHA256: cebd15d79f90c088ff2fde961231530e7dbb45b2f5968e002135edc5b695279b

```md
---
comet_change: browser-e2e
role: technical-design
canonical_spec: openspec
---

# Design: browser-e2e

## Context

现状：`apps/scripts/browser_e2e.py` 单文件（~300 行），5 个粗场景，双端对齐比较已验证可行（18/18 通过）。已知的浏览器层脆性来源均已定位：欢迎弹层异步挂载、kanban 按钮 hover 渲染、保存 POST 与列表刷新 GET 竞态。LLM 调用走 `.env` 真实 key（`load_dotenv(override=False)` 意味着显式环境变量可覆盖）。Playwright + Chromium 已就绪，PG 本机可用。

## 高层结构

```
apps/e2e/
├── run.py            # 入口：解析参数（--scenarios s03,s05 / --target zimeiti）→ 双端循环 → 对齐报告
├── runner.py         # TargetManager：spawn/就绪等待/teardown；zimeiti 注入 mock LLM 环境
├── mock_llm.py       # OpenAI 兼容流式 mock（uvicorn 线程，端口 18900）
├── helpers.py        # click_nav / dismiss_onboarding / syncMutation / sweep / 轮询原语
├── parity.py         # compare()：结构级观测值 diff（S5 语义内容差异仅 NOTE）
├── coverage_map.py   # API 路径 → 场景映射表（运行末打印）
├── scenarios/
│   ├── base.py       # Scenario 协议：run(page, ctx) -> dict（结构级观测值）
│   ├── s01_onboarding.py … s10_trends_topics.py
└── README.md         # 使用说明 + 覆盖映射表
```

运行方式：`cd apps/api && uv run python ../e2e/run.py`（复用 api venv 的 playwright/fastapi）；`make e2e-browser` 封装。

## 关键决策

### 1. LLM mock 边界（用户拍板：全链路真实 + LLM mock）

zimeiti 后端以显式环境变量启动：`OPENAI_API_KEY=sk-e2e-mock`、`OPENAI_BASE_URL=http://127.0.0.1:18900/v1`、`ZIMEITI_MODEL=mock-model`。`load_dotenv(override=False)` 保证显式变量优先于 `.env`。mock 端点实现 `/v1/chat/completions` 流式 SSE（`data: {"choices":[{"delta":{"content":...}}]}` + `[DONE]`），按消息内容返回确定性回复（含 `MOCK:` 前缀）。链路真实性：前端→HTTP→SSE→deepagents agent→langchain-openai 客户端→mock 端点→回程渲染，除「真模型推理」外全部真实。画像向导的 LLM 增强同样经此边界确定性化。

Easel 端保持自身配置（其网关读 Easel/.env，不受控）——S5 类场景对 Easel 侧只比较「气泡出现」等结构级事实，回复内容差异记 NOTE 不判失败。

### 2. 场景契约与双端对齐

每个场景 `run(page, ctx) -> obs`，obs 只含**结构级可比较观测值**（布尔、可达页面列表、错误计数）；语义内容（回复文本、数据条数）不入 obs。同一场景在两端执行，`parity.compare()` 逐键 diff：结构级必须一致，环境性差异显式 NOTE。

### 3. 网络同步取代固定 sleep

单文件版三轮调试确认的竞态全部以 `expect_response` 同步根治：写操作等其变更请求回包 + 后续列表 GET 回包再断言。导航后等列表 GET。弹层异步挂载用轮询等待。kanban 操作按钮 `display:none`→`:hover` 渲染，用 hover 后普通点击（force 对无布局盒元素无效）。

### 4. 数据自清理与幂等

场景内创建的数据（选题/排期/画像/会话/输出 fixture）场景结束前删除；场景开始时按标题清扫历次残留。输出 fixture 由 runner 在 spawn 前直接写入两端数据目录（`outputs/e2e-fixture/note.md`），teardown 删除。

### 5. 环境与确定性

- 外部依赖数据（热点雷达抓微博/抖音）：页面渲染必断言，条目存在性为条件断言（无条目时记录 skip 理由，「做内容」跳转仅在有条目时执行）
- Windows：zimeiti spawn 前设 `WindowsSelectorEventLoopPolicy`（psycopg 异步要求，`python -m zimeiti_api` 已内置）；teardown 强杀 + 端口核对
- 端口：zimeiti 8110（避开用户 8000）、mock LLM 18900、Easel 7860（其默认）

## 风险与对策

| 风险 | 对策 |
|---|---|
| Easel 端真实 LLM 慢/失败 | S5 对 Easel 上限 180s，失败仅影响该端该场景，diff 报告明确归属 |
| 热点无数据 | 条件断言 + skip 记录 |
| 两端构建版本 UI 差异 | click_nav role→text 双重兜底（已在单文件版验证） |
| 场景间数据串扰 | 每场景独立清扫；会话类操作用独立会话名 |

```

## docs/openspec/changes/browser-e2e/tasks.md

- Source: docs/openspec/changes/browser-e2e/tasks.md
- Lines: 1-34
- SHA256: 9a8fad38e1537a1ffe4cb4fcafa487f663911b707cff390d67a1b076f4c05516

```md
# Tasks: browser-e2e

## 1. 套件骨架

- [ ] 1.1 `apps/e2e/` 目录：`runner.py`（TargetManager：spawn/就绪/teardown，zimeiti 注入 mock LLM 环境变量与 Windows 策略）
- [ ] 1.2 `mock_llm.py`：OpenAI 兼容 `/v1/chat/completions` 流式 mock（确定性回复、uvicorn 线程）
- [ ] 1.3 `helpers.py`：click_nav 双重兜底、欢迎弹层轮询处理、`sync_mutation` 网络同步原语、`poll_text`、数据清扫
- [ ] 1.4 `parity.py`：结构级观测值 diff（环境性差异 NOTE）+ `coverage_map.py` 映射表
- [ ] 1.5 `scenarios/base.py` 协议与 `run.py` 入口（`--scenarios`、`--target` 参数，退出码契约）

## 2. 十个用户路径场景

- [ ] 2.1 s01 首屏+引导弹层（异步挂载轮询、跳过、工作台渲染）
- [ ] 2.2 s02 侧栏 6 页 + 工具子导航 5 页全导航（无未捕获 JS 错误）
- [ ] 2.3 s03 选题 CRUD：新建（POST+GET 同步）→ 列表出现 → 删除 → 归零 + 残留清扫
- [ ] 2.4 s04 选题→排期→内容日历出现条目→清理（POST /api/schedule 同步）
- [ ] 2.5 s05 对话全链路：发送→流式开始→mock 回复渲染→完成→新建会话→切换→删除（confirm 对话框）
- [ ] 2.6 s06 内容库：树渲染→打开 fixture 文件→预览内容断言（fixture 由 runner 预置/清理）
- [ ] 2.7 s07 画像：列表→创建向导（mock LLM 增强）→出现在列表→删除
- [ ] 2.8 s08 账号页渲染 + whoami 状态结构
- [ ] 2.9 s09 设置面板：模型通道行渲染可见
- [ ] 2.10 s10 热点雷达：页渲染（条件断言）→有条目时「做内容」跳转对话页预填

## 3. 集成与切换

- [ ] 3.1 删除 `apps/scripts/browser_e2e.py`
- [ ] 3.2 Makefile `e2e-browser` 指向新入口；`apps/e2e/README.md`（使用说明+覆盖映射表）
- [ ] 3.3 lint/format 通过（ruff 对 apps/e2e 或豁免配置）

## 4. 验证

- [ ] 4.1 全量套件双端跑通：全部场景 PASS、双端结构差异 0
- [ ] 4.2 稳定性：连续 3 轮全绿、测试数据零残留
- [ ] 4.3 `make check`（既有门禁）全绿不回归

```

## docs/openspec/changes/browser-e2e/specs/browser-e2e-suite/spec.md

- Source: docs/openspec/changes/browser-e2e/specs/browser-e2e-suite/spec.md
- Lines: 1-102
- SHA256: 845fb96553da0897a2cbc74f1f0fcf15fec5576365f40655de38f3cc13b8feaa

[TRUNCATED]

```md
# browser-e2e-suite 能力规范

## Purpose

提供覆盖产品全部用户路径的浏览器级自动化测试：以真实 Chromium 模拟用户操作，在 zimeiti 与 Easel 双端跑同一套旅程并断言行为一致；LLM 调用在测试边界 mock（OpenAI 兼容流式端点），其余链路（前端、HTTP、SSE、PG、业务逻辑）全部真实。作为 API 级 parity（57 项）之上的用户路径行为契约。

## ADDED Requirements

### Requirement: 套件以独立目录组织并按用户路径拆分场景

浏览器自动化测试必须位于 `apps/e2e/` 独立目录，每个用户路径一个场景模块；旧的单文件实现必须删除。入口必须支持：全量跑、按场景名单跑、单端跑（调试）。

#### Scenario: 全量运行双端对齐

- **WHEN** 执行 `make e2e-browser`
- **THEN** 套件依次在 zimeiti(:8110) 与 Easel(:7860) 上跑全部场景，输出每项 PASS/FAIL 与双端差异，任一失败退出码非 0

#### Scenario: 旧单文件不再存在

- **WHEN** 检查仓库
- **THEN** `apps/scripts/browser_e2e.py` 不存在，其行为已全部由 `apps/e2e/` 场景覆盖

### Requirement: 每个用户路径都有真实链路场景

每个有 UI 入口的用户路径必须有一个场景以真实浏览器操作走通完整链路（页面渲染→用户操作→网络请求→UI 反馈）；LLM 响应可在测试边界 mock。无 UI 入口的路径必须显式登记由 API 级 parity 覆盖。

#### Scenario: 对话全链路（mock LLM）

- **WHEN** 用户在对话页输入消息并发送
- **THEN** 请求经 SSE 到达后端并调用（被 mock 的）模型，打字机效果渲染回复，流结束后输入区恢复可发送状态

#### Scenario: 选题创建后出现在看板

- **WHEN** 用户在选题库点击新建、填写标题并保存
- **THEN** 保存请求成功且新卡片出现在看板对应列

#### Scenario: 选题可排期并反映到日历

- **WHEN** 用户对某选题点击排期并确认
- **THEN** 排期请求成功，内容日历出现该条目

#### Scenario: 内容库文件可预览

- **WHEN** 用户在内容库点开一个已存在的文本文件
- **THEN** 预览区渲染该文件内容

#### Scenario: 画像向导真实创建

- **WHEN** 用户走完画像创建向导（填表提交，LLM 增强被 mock）
- **THEN** 新画像出现在画像列表，且可被删除

#### Scenario: 设置面板反映模型通道

- **WHEN** 用户打开设置面板
- **THEN** 已配置的模型通道行渲染可见

#### Scenario: 热点可跳转做内容

- **WHEN** 热点雷达存在热点条目且用户点击其「做内容」
- **THEN** 跳转到对话页且输入框预填该选题

#### Scenario: 会话管理

- **WHEN** 用户在对话页新建会话、切换会话、删除会话
- **THEN** 会话列表与消息区随操作正确变化（删除需确认）

#### Scenario: 首次引导

- **WHEN** 首次访问（localStorage 无标记）
- **THEN** 出现欢迎引导弹层，可跳过进入工作台

#### Scenario: 全页面导航可达

- **WHEN** 用户依次点击全部导航项（侧栏 6 页 + 工具子导航 5 页）
- **THEN** 每页渲染成功且无未捕获 JS 错误

### Requirement: 双端行为一致性是验收判据

同一场景在两端的可比较观测值（结构级布尔/列表）必须一致；因数据或 LLM 配置导致的语义内容差异（如回复文本、数据条数）只报告不判失败。


```

Full source: docs/openspec/changes/browser-e2e/specs/browser-e2e-suite/spec.md
