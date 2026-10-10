# 提案：zimeiti_api 包架构重组（arch-restructure）

## Why

快速迭代后 `zimeiti_api` 包已积累 35 个平铺 py 模块（内容/运营/治理/运行时/平台混在
同一层），测试目录同样平铺且存在 `test_p1_batch1/2` 这类与结构无关的命名——新人
无法从目录读懂系统边界，导入关系也失去层次约束。参考项目组织方式：Easel 的
`easel/commands` 按职责分包 + `skills/openclaw/skill-*` 能力单元化；xiaobei 的
`crews/<crew>/skills/<name>` 能力边界清晰。本次变更把包结构对齐这一组织哲学，
同时把开发流程收回 Comet Classic（本变更即流程回归后的第一个变更）。

## What Changes

- `src/zimeiti_api/` 35 个平铺模块按领域移动为 6 个子包（**纯移动，零行为变更**）：
  - `core/`：audit、credentials、alias（原 credentials_alias）、seal、notify、models
  - `governance/`：compliance、risk、platform_state、preflight、publisher（执行器=护栏）
  - `platforms/`：gzh、xhs、xhs_readback（移入）、themes（移入）
  - `content/`：topics、creation、dna、templates、profiles
  - `operations/`：metrics（原 ops_metrics）、daily（原 ops_daily）、calibration、report_page、postmortem、kanban
  - `runtime/`：graph、tools、hosted、hosted_daily、gateway、checkpoints、health
  - 顶层保留：`app.py`（uvicorn 入口）、`config.py`（宪法规定的全局锚点）、`__init__.py`
- `apps/api/tests/` 镜像重组为同名子包目录；`test_p1_batch1/2` 按模块拆分归位
- `scripts/*.py`、`Makefile`、`scripts/*.bat`、`AGENTS.md` 中的模块路径与
  `python -m` 入口同步更新（seal/gateway/ops_daily/hosted_daily/xhs_readback/
  templates/dna/postmortem 共 8 个入口）
- **不留旧路径 re-export 双轨**（避免两套真相），全量更新导入

## Capabilities

- **New Capabilities**: 无（本变更不改行为规格）
- **Modified Capabilities**: 无（HTTP 契约、CLI 参数、审计事件名全部不变）

## Non-Goals

- 不改任何行为逻辑（纯移动 + 导入更新）
- 不动 `vendor/`（宪法：上游一字不差）
- 不改 HTTP 路径、CLI 参数签名、审计 action 名
- 不做文件名以外的重命名优化（如类改名）——控制 diff 半径

## 关键决策

- **skip_specs**: 纯重构无行为规格变化，`.openspec.yaml` 显式 `skip_specs: true`
- **入口兼容**: `python -m` 路径全部更新为新位置（bat/Makefile 同步），不保留
  旧路径垫片——配置与脚本本仓库内闭环，无外部消费者
- **tdd_mode=direct**: 验证手段是全量回归（174 tests）+ 入口冒烟，不新增测试先行
