# Comet Design Handoff

- Change: gate-compliance
- Phase: design
- Mode: compact
- Context hash: 7506886119d1f5c7c50684f7a80ac262f1da4169fe0f20f34bec90204d99c31e

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/gate-compliance/proposal.md

- Source: docs/openspec/changes/gate-compliance/proposal.md
- Lines: 1-31
- SHA256: 1c2d6ab02ffbfb989f7fb2b70174cdcd7d12de1efd8009fdde300924a7f26d5c

```md
# gate-compliance —— 后端质量门禁对齐 Comet 家规

## Why

backend-restructure 归档后的后端（apps/api）与 comet-integration 家规门禁（`scripts/check-api.sh`：ruff format → ruff lint → mypy → bandit → pytest+coverage≥80%）全面不达标：30/36 文件需重整格式、mypy/bandit/pytest-cov 未安装未声明、测试仅 1 文件 12 用例（家规 36 文件 256 用例）、覆盖率无从度量。测试证据是 Comet build/verify 阶段的硬门禁，缺测试即无法验收。

## What Changes

- pyproject dev 依赖组补齐 `ruff`/`mypy`/`bandit`/`pytest-cov`（当前仅 pytest）
- Makefile 新增 `check` 目标：五道门禁一键执行（对齐家规 check-api.sh，适配 uv 与 Windows）
- ruff format 全量重整 + ruff lint 错误清零
- bandit 安全扫描通过（排除测试 assert、处理 subprocess 类告警）
- mypy 类型检查通过（对迁移代码补类型或以明确策略收敛配置）
- 测试从 12 用例扩至覆盖 ≥80%：core（pg/paths/settings/dotenv/timeouts）、governance（guard）、platforms（accounts/analytics/login/publish/wechat/common）、content（ideas/outputs/personas/persona_core/schedule/skills/trends/uploads）、operations（env/models）、runtime（chat/status）
- **行为零变化**：不新增/删除/修改任何 API 端点行为，路由面保持 52 个唯一 api 路径

## Capabilities

### New Capabilities

- `backend-quality-gates`: 后端质量门禁的定义与执行——五道门禁（format/lint/types/security/tests+coverage）的可执行命令、达标阈值（coverage≥80%）与行为零回归约束

### Modified Capabilities

- 无（backend-structure 的结构要求不变，本变更仅在其上补质量门禁）

## Impact

- 代码：apps/api 全部源文件的格式化与类型标注；apps/api/tests/ 大幅扩充；Makefile、pyproject.toml
- 不影响：API 行为、数据库 schema、skills 资产、前端
- 风险：mypy 对无类型迁移代码的首跑错误量大，需在 design 阶段定达标策略

```

## docs/openspec/changes/gate-compliance/design.md

- Source: docs/openspec/changes/gate-compliance/design.md
- Lines: 1-47
- SHA256: a1a0d3de29731a2bd186d172f994732bbe5ebd980e732f6ba0bee31351b494db

```md
---
comet_change: gate-compliance
role: technical-design
canonical_spec: openspec
status: final
---

# gate-compliance 设计

## Context

backend-restructure（已归档）把 easel 单体拆为 zimeiti_api 六域分包，但质量基建仍是 phase1 复制时的最低配置：pytest 仅 dev extra 里的 12 个用例，无 mypy/bandit/pytest-cov；Makefile 只有 verify（openclaw 归零 + 技能校验）。家规门禁来自 comet-integration 的 `scripts/check-api.sh`，但两条线布局不同（那边 src layout），不能直接搬脚本，需要在当前布局上重建等价门禁。

关键约束：
- Windows 开发环境（uv venv，`Scripts/python.exe`），控制台 GBK——所有门禁命令需 `PYTHONUTF8=1`
- 迁移代码 ~4700 行基本无类型标注，mypy 首跑错误量不可控
- 大量端点依赖外部服务（Playwright 取数、微信公众号 API、LLM、登录子进程），测试必须 mock 边界
- 行为零回归是硬约束（backend-restructure 的 A7 成果不可回退）

## Goals / Non-Goals

**Goals:**
- `make check` 一键五道门禁全绿，可作为 Comet check run 证据命令
- coverage ≥80%，测试按域组织、外部依赖全部 mock
- 行为零回归（路由 52、既有验收脚本全过）

**Non-Goals:**
- 不改任何 API 行为/路由/数据库 schema
- 不做 src-layout 迁移（flat 布局为既定决策）
- 不处理 skills 目录的 77 处 Easel 版式路径债务
- 不合并两条产品线（h2pl vs comet-integration）

## Decisions

1. **Makefile `check` 目标内联五步**（而非搬 check-api.sh）：当前布局 `apps/api` 非 src layout，家规脚本不适用；内联保持家规的步骤顺序与阈值语义。
2. **mypy 达标策略：宽松起步 + 增量收紧**。`pyproject.toml` 配 `check_untyped_defs = true`（函数体仍检查）+ `ignore_missing_imports = true`（biliup 等无 stub），必要时对个别遗留文件 `# type: ignore` 定点豁免并在注释说明。不做全量补类型——那是长期工程，不属本变更。首跑若错误仍超预期，按文件按规则逐步收敛直至清零。
3. **bandit 配置**：`-x` 排除无 vendor 可排，改用 `-s B101`（测试 assert）+ 对 subprocess 用法（登录子进程是产品行为）按需定点 `# nosec` 并注明理由。
4. **测试组织**：按域分文件（tests/test_<域>_<面>.py），conftest 提供：PG 测试库 fixture（复用既有 conftest 的库/uid 租户隔离）、TestClient fixture（base_url 带 TrustedHost 允许的 host）、事件循环策略。外部边界 mock：agent_runtime（chat 注入假 ask/run_turn）、subprocess（登录/发布/whoami）、httpx/Playwright（趋势/分析）。
5. **chat 的 LLM 依赖**：`runtime/chat.py` 对 `agent_runtime` 的调用通过模块属性引用，测试中 `monkeypatch` 掉 ask/run_turn 为假实现，验证路由契约（200/SSE 字段/持久化）而非 LLM 行为。
6. **覆盖率兜底顺序**：先补高价值纯逻辑（core/governance/content CRUD），再 mock 平台端点，最后对难以安全覆盖的外部执行路径（agent_runtime 的 LLM 调用体）以精确的分支测试 + 少量 `# pragma: no cover`（仅限真正无法离线到达的行）收敛到 ≥80%。

## Risks / Trade-offs

- mypy 宽松配置起步 → 类型保障弱于家规严格档；换取本变更可交付，后续变更逐步收紧
- pytest-cov 首跑覆盖率可能显著低于 80% → 测试扩充是本变更主要工作量，按域迭代推进
- mock 与真实行为的偏差 → 平台端点测试断言路由契约（状态码/结构）而非业务输出，与 e2e_parity_check 的运行级验收互补
- Windows 下 make + uv 的组合 → 全部命令已在会话内验证过等价形式

```

## docs/openspec/changes/gate-compliance/tasks.md

- Source: docs/openspec/changes/gate-compliance/tasks.md
- Lines: 1-31
- SHA256: ead9c77cca5097bfecb3e0e7b0bc58d7c4f8f89e3183e7268014876f9afc9e0e

```md
# gate-compliance 任务清单

## 1. 工具链与门禁入口

- [ ] 1.1 pyproject dev 依赖补 ruff/mypy/bandit/pytest-cov，`uv sync --all-extras` 安装
- [ ] 1.2 Makefile 新增 `check` 目标：ruff format → ruff lint → mypy → bandit → pytest+cov≥80（PYTHONUTF8=1）
- [ ] 1.3 ruff format 全量重整（apps/api 源码与测试）

## 2. 静态门禁清零

- [ ] 2.1 ruff lint 错误清零（含 app.py 与 zimeiti_api 全包）
- [ ] 2.2 bandit 扫描通过（-s B101 + subprocess 类告警定点 nosec 注明理由）
- [ ] 2.3 mypy 通过（check_untyped_defs + ignore_missing_imports 起步，逐文件收敛至零错误）

## 3. 测试扩充（cov ≥80%）

- [ ] 3.1 conftest 完善：PG 测试库 + TestClient（TrustedHost 兼容）+ 事件循环策略 fixture
- [ ] 3.2 core 域测试：pg（扩展现有 12 项）、paths（路径安全函数）、settings、dotenv、timeouts
- [ ] 3.3 governance 域测试：guard 中间件（写保护/TrustedHost/origin）
- [ ] 3.4 content 域测试：ideas/schedule/outputs/uploads/skills/trends 路由 CRUD（PG fixture）+ personas/persona_core
- [ ] 3.5 platforms 域测试：accounts/analytics/login/publish/wechat 路由契约（mock subprocess/httpx/Playwright）
- [ ] 3.6 operations 域测试：env/models 设置面板路由（ENV_FILE fixture）
- [ ] 3.7 runtime 域测试：status 全覆盖 + chat 契约（monkeypatch agent_runtime）+ agent_runtime 配置分支
- [ ] 3.8 覆盖率迭代至 ≥80%，对真正无法离线到达的行定点 pragma（注明理由）

## 4. 验证与收尾

- [ ] 4.1 `make check` 全绿
- [ ] 4.2 行为零回归：verify_openclaw_removal PASS（52 api routes）+ verify_pg_data_layer restart 4/4
- [ ] 4.3 双服务 E2E 抽查：e2e_parity_check 与 Easel 全部一致
- [ ] 4.4 提交、独立验收（verify 阶段）、归档

```

## docs/openspec/changes/gate-compliance/.openspec.yaml

- Source: docs/openspec/changes/gate-compliance/.openspec.yaml
- Lines: 1-2
- SHA256: cd54fe01555559ffd5cf6f7f1d1b06209492e5ba9147cdc3800201c09e2291d0

```md
schema: spec-driven
created: 2026-10-14

```

## docs/openspec/changes/gate-compliance/specs/backend-quality-gates/spec.md

- Source: docs/openspec/changes/gate-compliance/specs/backend-quality-gates/spec.md
- Lines: 1-39
- SHA256: 540c5f3507a959c1a2847a38be72af57b09c7f2d330e1eba3ce2750c68f58734

```md
# backend-quality-gates —— 后端质量门禁

## Purpose

定义后端（apps/api）质量门禁的统一入口与达标标准，使 Comet build/verify 阶段能用单一命令（`make check`）取得可录制、可复核的质量证据，替代"仅凭任务内定验收指标"的低标准闭环。

## ADDED Requirements

### Requirement: 门禁统一入口
后端质量门禁必须由 Makefile `check` 目标一键执行，依次运行：ruff format → ruff lint → mypy → bandit → pytest+coverage，任一步失败即门禁失败。

#### Scenario: 全绿门禁
- **WHEN** 在仓库根执行 `make check`
- **THEN** 五道门禁全部通过，退出码 0，输出含「全部门禁通过」

#### Scenario: 单道失败即拦截
- **WHEN** 任一门禁步骤检出问题（如 lint 错误或覆盖率低于阈值）
- **THEN** `make check` 非零退出并指出失败步骤，不继续执行后续步骤产生噪音

### Requirement: 覆盖率阈值
pytest 必须带 coverage 度量且总覆盖率 ≥80%（`--cov-fail-under=80`），度量对象为 `zimeiti_api` 包。

#### Scenario: 覆盖率达标
- **WHEN** 执行 `make check` 的 pytest 步骤
- **THEN** coverage 报告显示 zimeiti_api 总覆盖率 ≥80%，低于阈值时门禁失败

### Requirement: 行为零回归
门禁改造不得改变任何 API 端点的行为：唯一 api 路径集合保持 52 个，既有验收脚本（verify_openclaw_removal、e2e_parity_check、verify_pg_data_layer）保持通过。

#### Scenario: 路由面不变
- **WHEN** 门禁改造完成后运行 `verify_openclaw_removal.py`
- **THEN** 报告 52 个 api 路由，与 backend-restructure 归档时一致

### Requirement: 工具链声明
ruff、mypy、bandit、pytest-cov 必须在 pyproject dev 依赖组中声明，保证 `uv sync --all-extras` 后门禁可在干净环境复现。

#### Scenario: 干净环境复现
- **WHEN** 新环境执行 `uv sync --all-extras` 后运行 `make check`
- **THEN** 无需手工安装任何门禁工具即可完整执行

```
