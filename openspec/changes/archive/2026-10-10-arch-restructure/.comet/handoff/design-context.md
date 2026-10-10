# Comet Design Handoff

- Change: arch-restructure
- Phase: design
- Mode: compact
- Context hash: 12a282c5cc7a703e326af75c3fcaa31601b3dafe3cdab0bbdd0f7878eff1b69b

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/arch-restructure/proposal.md

- Source: openspec/changes/arch-restructure/proposal.md
- Lines: 1-45
- SHA256: 67eceb34e22e9ffe242667ab673414e415237af09f3cc61ebc92af6b082463f5

```md
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

```

## openspec/changes/arch-restructure/design.md

- Source: openspec/changes/arch-restructure/design.md
- Lines: 1-70
- SHA256: 43268659bea8a95fdb597a38f6394e7ef1175b58a9a0bacf71f26853377b133b

```md
---
comet_change: arch-restructure
role: technical-design
canonical_spec: openspec
---

# 设计：arch-restructure

## Context

`zimeiti_api` 35 个平铺模块 + 27 个平铺测试文件，导入无层次约束（任何模块可
import 任何模块）。入口矩阵：8 个 `python -m` 入口、`zimeiti_api.app:app`
（uvicorn）、`zimeiti_api.gateway`，被 Makefile/2 个 bat/6 个 scripts/*.py 引用。
参考组织：Easel `easel/commands` 职责分包、`skills/openclaw/skill-*` 能力单元；
xiaobei `crews/<crew>/skills/<name>` 能力边界。本变更只移动文件与更新导入，
不改任何行为（见 proposal）。

## Goals / Non-Goals

- Goals：领域分层目录；导入层次可见；测试镜像同构；入口矩阵全部可用
- Non-Goals：行为变更、vendor 改动、API 契约变更、旧路径兼容垫片

## 目标布局（决策 D1）

```
zimeiti_api/
├── app.py / config.py / __init__.py      # 顶层入口与全局锚点（宪法：config 绝对锚定）
├── core/        audit credentials alias seal notify models
├── governance/  compliance risk platform_state preflight publisher
├── platforms/   gzh xhs xhs_readback themes      # 已有包，移入 2 个
├── content/     topics creation dna templates profiles
├── operations/  metrics daily calibration report_page postmortem kanban
├── runtime/     graph tools hosted hosted_daily gateway checkpoints health
└── vendor/      # 不动（宪法）
```

分层依赖规则（单向，D2）：`runtime → {governance, platforms, content,
operations, core}`；`governance → core/platforms`；`content/operations/platforms
→ core`；`core` 不依赖业务包。`app.py` 顶层只做组装（对齐 main.ts 组装器惯例）。

## 决策记录

- **D1 布局按领域而非技术层**：governance（宪法护栏）/content/operations/runtime
  与 PRD 能力域一一对应；`publisher.py` 归 governance（频控/白名单是护栏职责
  而非平台适配）。
- **D2 模块改名最小化**：仅去 `ops_` 前缀（metrics/daily/calibration/report_page）
  与 `credentials_alias → core/alias`；类名/函数名不动，控制 diff 半径。
- **D3 入口全量更新不留垫片**：8 个 `python -m` 入口路径更新（seal→core.seal、
  gateway→runtime.gateway、ops_daily→operations.daily、hosted_daily→
  runtime.hosted_daily、xhs_readback→platforms.xhs_readback、templates/dna/
  postmortem→各自子包），Makefile/bat/AGENTS.md/scripts 同步。
- **D4 测试镜像同构**：`tests/{core,governance,content,operations,runtime,
  platforms}`；`test_p1_batch1/2` 按被测模块拆分归位（postmortem/dna/templates/
  alias/themes 测试进对应目录）。
- **D5 验证策略**：tdd_mode=direct——纯重构以「移动前后测试集合等价 + 全量
  回归 + 8 入口冒烟 + 旧路径残留 grep 为零」为验收，不新增测试。

## 迁移步骤（tasks 的执行序）

1. `git mv` 建子包骨架（含 `__init__.py`）
2. 全局导入重写（src/tests/scripts 的 `zimeiti_api.X` → 新路径；循环导入排查）
3. 入口矩阵更新（Makefile/bat/AGENTS.md）
4. 测试拆分归位
5. 全量回归 + 冒烟 + grep 验收

## Risk

- 循环导入浮现（原平铺时被掩盖）→ 移动后即刻全量 import 检查，环依赖就地
  用局部导入化解（保持现有语义，不重构）
- Windows 文件锁（gateway 正在运行）→ 重构前停网关进程

```

## openspec/changes/arch-restructure/tasks.md

- Source: openspec/changes/arch-restructure/tasks.md
- Lines: 1-30
- SHA256: 9aecf5553f1bd178e9d5afc6cc582a6a8ce71374467308b8d9ed6809392abbd7

```md
# 任务：arch-restructure

> 模板任务引用 comet-task-ref 惯例；tdd_mode=direct，验证=全量回归+冒烟+grep。

## 1. 停机与骨架

- [ ] T1 停止 :8000 网关进程（Windows 文件锁规避），确认 MCP 不受影响
- [ ] T2 `git mv` 建六个子包骨架并移动模块（含 `__init__.py`）：
      core/ governance/ platforms/（移入 xhs_readback, themes）/ content/
      operations/（ops_* 去 4 前缀）/ runtime/

## 2. 导入重写

- [ ] T3 src 全量导入更新（`zimeiti_api.X` → 子包路径），含 config 锚点不动
- [ ] T4 循环导入排查：`uv run python -c "import zimeiti_api.app"` 全链导入通过
- [ ] T5 8 个 `python -m` 入口更新：Makefile / scripts/run_ops_daily.bat /
      run_hosted_daily.bat / scripts/walkthrough_*.py / xhs_readback 调用点

## 3. 测试镜像

- [ ] T6 tests 按子包目录归位（27 个文件 git mv）
- [ ] T7 test_p1_batch1/2 按被测模块拆分归位（postmortem/dna/templates/alias/themes）
- [ ] T8 conftest.py 与测试内部导入路径更新

## 4. 验收

- [ ] T9 make check 全绿（等价测试集 174 项，覆盖率 ≥80%）
- [ ] T10 入口冒烟：8 个 `python -m --help` 全部可用 + `zimeiti_api.app:app` 可导入
- [ ] T11 grep 验收：`zimeiti_api\.(ops_metrics|ops_daily|ops_calibration|ops_report_page|credentials_alias|publish_queue)` 零残留
- [ ] T12 AGENTS.md 目录结构段更新

```

## openspec/changes/arch-restructure/.openspec.yaml

- Source: openspec/changes/arch-restructure/.openspec.yaml
- Lines: 1-3
- SHA256: 9fb84f0658a7a2924fd716c5fa528a0e5dc4b5979deff93672db6b4259942abe

```md
schema: spec-driven
created: 2026-10-10
skip_specs: true

```
