# Comet Design Handoff

- Change: stale-process-guard
- Phase: design
- Mode: compact
- Context hash: 9292eb28b5d44a166d6f61cc2b541bfad1ae82835d528875e037cfed02c8ae1c

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/stale-process-guard/proposal.md

- Source: docs/openspec/changes/stale-process-guard/proposal.md
- Lines: 1-52
- SHA256: bf837f1b02d6060f8daa690be68d0a00bece253cd300d6e966be6b9abf51e8ff

```md
---
comet_change: stale-process-guard
---

# stale-process-guard：代码变更后未重启的进程守卫

## Why

harness-business-split 分层重构后，用户实测报障：

```
Error: ❌ 运行时初始化失败：No module named 'zimeiti_api.memory.tools'
```

取证结论：
- 当前代码**全新起服务对话完全正常**（复现验证）——不是代码回归
- 根因：用户的长跑服务进程启动于重构之前；`agent_runtime` 对
  `memory.tools` 的**函数级懒加载**在首次建 agent 时按包 `__path__`
  （磁盘目录）解析——`zimeiti_api/memory/` 已被 git mv 走 → ImportError
- **验证盲区**（我的责任）：E2E 每次起全新子进程服务，「重构后未重启的
  长跑进程」这个形态永远测不到；`make verify` 脚本还因期望值过期
  （路由 52→57）早已失效且无人发现——两个脚本都不在 make check 里

## What Changes

- **启动指纹 + 运行时守卫**（`zimeiti_harness/runtime/fingerprint.py`）：
  进程启动时对 `zimeiti_api/` + `zimeiti_harness/` 源码取内容哈希快照；
  chat 入口（run_turn/ask/ask_sync/chat_structured）执行前比对当前磁盘
  指纹，不一致 → 明确错误「后端代码已变更，请重启后端」而非 cryptic
  ImportError
- **`make verify` 修复并收编**：`verify_openclaw_removal.py` 的 import 与
  文件路径跟随 harness 分层更新；路由期望 52→57；`make verify` 接入
  `make check`（防止这类脚本再次悄悄失效）
- **README 故障排查**：补「重构/更新代码后必须重启后端」条目

## Non-Goals

- 不追求 mtime/内容级精确 diff 报告（哈希不一致即提示重启，足够）
- 不做前端热重载联动（后端重启本就需用户操作，守卫只负责把话说清楚）

## Capabilities

### New Capabilities

- `stale-process-guard`：后端进程启动后源码若发生变更，chat 请求返回可行动的
  中文错误（含重启指引）而非模块解析异常

## Impact

harness 新增 1 个模块（无外部依赖）；agent_runtime 四个入口加一行守卫；
Makefile 接线；verify 脚本修复；README 增补。运行行为零变化（指纹一致时
守卫为 no-op）。

```

## docs/openspec/changes/stale-process-guard/design.md

- Source: docs/openspec/changes/stale-process-guard/design.md
- Lines: 1-54
- SHA256: ec8ebabe519ab6f0b11582220bad6cb99eed988fedcd2f886f7c0fb15976d27c

```md
---
comet_change: stale-process-guard
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：stale-process-guard

## 高层方案

```
zimeiti_harness/runtime/fingerprint.py
  capture()   -> dict        # 进程启动时调用：{head, files: {path: sha1}} 存模块级快照
  current()   -> dict        # 重算当前磁盘指纹
  ensure_fresh() -> None     # 比对；不一致 raise StaleProcessError(可行动文案)
  _hash_tree()               # sha1(zimeiti_api/**/*.py + zimeiti_harness/**/*.py)，
                             # 排除 __pycache__/测试；60s TTL 缓存（防每请求全量哈希）

agent_runtime 入口（run_turn / ask / ask_sync / chat_structured）
  首行：fingerprint.ensure_fresh()   # 不一致即抛，文案含重启指引
```

## 关键决策

### D1：内容哈希而非 mtime
git checkout/merge 会重写文件（mtime 变、内容不变），mtime 指纹会误报。
sha1 内容哈希只在内容真变时变。~100 个小文件全量哈希 <50ms，配 60s TTL
缓存，每请求开销可忽略。

### D2：守卫放 harness 入口而不是 chat_router
懒加载 import 炸在 harness 内部（`from ..memory.tools import`），守卫必须在
**同一层的最早期**——harness 的四个公开入口首行。chat_router 只管转发。

### D3：错误文案给动作不给现象
「❌ 后端代码已变更（进程启动于旧版代码）——请重启后端（Ctrl+C 后重新
make api / make dev）再试。」用户不需要知道什么是 ImportError。

### D4：make verify 收编进 make check
这次事故里 verify 脚本失效数月无人知（不在门禁里）。接入 check 后，
脚本自身破坏（import 错、期望值过期）会当场红。

## 风险与对策

- **风险**：指纹文件遍历在 Windows 大小写/路径分隔符不稳定 → 用相对路径
  POSIX 风格（as_posix）+ sorted，跨平台确定
- **风险**：60s TTL 内重启后仍报旧态 → TTL 只影响「变更后多久被发现」，
  最坏 60s，可接受；进程重启时快照自然重建
- **风险**：开发中改代码忘重启被拦 → 正是设计目的（现在的报错从
  「No module named」变成「请重启」，方向正确）

## Open Questions

无。

```

## docs/openspec/changes/stale-process-guard/tasks.md

- Source: docs/openspec/changes/stale-process-guard/tasks.md
- Lines: 1-21
- SHA256: 4104ed40e67f5b39795ef8dc7d452b01418678ecfa9cbeaed087f9faccc7ecf4

```md
---
comet_change: stale-process-guard
---

# Tasks：stale-process-guard

## 1. 指纹守卫

- [ ] 1.1 `zimeiti_harness/runtime/fingerprint.py`：capture/current/ensure_fresh（D1 内容哈希+D2 同层入口） <!-- comet-task:22de58ff-24e8-4f7e-bad3-f122c953b92e -->
- [ ] 1.2 agent_runtime 四入口（run_turn/ask/ask_sync/chat_structured）首行接入；app.py lifespan capture <!-- comet-task:82817e79-fa20-4949-84be-0650f28f1c7a -->
- [ ] 1.3 单测：指纹一致放行/不一致拦截（文案含重启指引）/哈希稳定性（同内容不变） <!-- comet-task:e4a97bd0-d166-4139-b13c-cba3916c39a1 -->

## 2. verify 收编与文档

- [ ] 2.1 verify_openclaw_removal.py 路径+期望值修复（已完成，随本次提交）；make verify 接入 make check（D4） <!-- comet-task:55b3a76f-515e-497f-9d6e-189efc1c5319 -->
- [ ] 2.2 README 故障排查补「代码变更后必须重启后端」 <!-- comet-task:47f4c269-5ea5-4bc8-872e-d3c4bbc501a3 -->

## 3. 验证

- [ ] 3.1 make check 全绿（含新守卫单测+verify）；探针：模拟指纹不一致返回重启文案 <!-- comet-task:5667c6a5-492b-44ab-8ccf-e67820c91558 -->
- [ ] 3.2 E2E 63/63 不回归 <!-- comet-task:d7ce56c6-cc52-42ca-a487-3cfb6e993151 -->

```

## docs/openspec/changes/stale-process-guard/.openspec.yaml

- Source: docs/openspec/changes/stale-process-guard/.openspec.yaml
- Lines: 1-2
- SHA256: 4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9

```md
schema: spec-driven
created: 2026-10-17

```

## docs/openspec/changes/stale-process-guard/specs/stale-process-guard/spec.md

- Source: docs/openspec/changes/stale-process-guard/specs/stale-process-guard/spec.md
- Lines: 1-33
- SHA256: d1435ccd930288d86b72e3e4dbad1591eef11b7873e85803d29da73083ad3bff

```md
# stale-process-guard 规格草案

## Purpose

代码在进程启动后被变更（重构/移动模块/拉取更新）时，用户得到可行动的重启提示，
而不是 `No module named ...` 这类无法定位的模块解析异常。

## ADDED Requirements

### Requirement: 启动指纹与运行时守卫

系统 SHALL 在进程启动时对后端源码（zimeiti_api/ 与 zimeiti_harness/ 的 .py）
计算内容哈希快照；chat 类入口（run_turn / ask / ask_sync / chat_structured）
MUST 在执行前比对当前磁盘指纹，不一致时 SHALL 抛出含重启指引的中文错误，
且 MUST NOT 尝试继续执行可能触发 ImportError 的懒加载路径。

#### Scenario: 指纹一致放行
- **WHEN** 源码未变更（正常情况）
- **THEN** 守卫为 no-op，对话正常进行

#### Scenario: 指纹不一致拦截
- **WHEN** 进程启动后源码被移动/修改（如分层重构、git pull）
- **THEN** 返回「❌ 后端代码已变更（进程启动于旧版）——请重启后端
  （Ctrl+C 后重新 make api / make dev）再试」，不出现 ImportError 文本

### Requirement: verify 脚本随分层更新且收编进门禁

`verify_openclaw_removal.py` MUST 跟随 harness 分层后的路径；`make verify`
SHALL 接入 make check，防止验收脚本悄悄失效。

#### Scenario: make verify 通过
- **WHEN** 运行 make verify（或 make check）
- **THEN** openclaw 归零校验、路由数、runtime API 完整性检查全部通过

```
