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
