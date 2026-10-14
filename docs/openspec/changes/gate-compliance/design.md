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
