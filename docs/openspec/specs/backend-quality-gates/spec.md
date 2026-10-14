# backend-quality-gates Specification

## Purpose
定义后端（apps/api）质量门禁的统一入口与达标标准，使 Comet build/verify 阶段能用单一命令（`make check`）取得可录制、可复核的质量证据，替代"仅凭任务内定验收指标"的低标准闭环。

## Requirements

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
