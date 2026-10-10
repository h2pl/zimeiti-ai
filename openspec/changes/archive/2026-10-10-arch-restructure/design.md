---
comet_change: arch-restructure
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-10-arch-restructure
status: final
---

# 设计：arch-restructure

## Context

`zimeiti_api` 34 个平铺模块（不含 platforms/__init__） + 27 个平铺测试文件，导入无层次约束（任何模块可
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
  **实施修正（独立评审 W1）**：分层规则描述的是目标方向；现状存在函数内惰性的
  逆向依赖（governance/queue → runtime.tools；operations/metrics → governance/
  platforms——平铺时代的真实依赖被如实搬运，import 期无环）。待后续变更治理，
  本变更不改行为。
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
