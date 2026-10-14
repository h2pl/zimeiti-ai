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
