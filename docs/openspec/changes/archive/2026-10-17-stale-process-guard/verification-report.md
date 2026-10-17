---
comet_change: stale-process-guard
---

# 验证报告：stale-process-guard（代码变更未重启守卫）

## 用户报障根因（取证记录）

报障：对话返回 `❌ 运行时初始化失败：No module named 'zimeiti_api.memory.tools'`。

| 取证步骤 | 结果 |
|---|---|
| 当前代码全新起服务 + 真实对话 | **正常**（"你好！我是你的自媒体运营搭子…"）——非代码回归 |
| PG 全表扫描旧模块路径 | 0 条——非序列化状态问题 |
| 源码 grep 旧路径 | 0 处（静态）——非代码引用问题 |
| 结论 | 长跑进程（启动于 harness-business-split 重构前）的函数级懒加载按包 `__path__`（磁盘目录）解析，`zimeiti_api/memory/` 已被 git mv 走 → ImportError |

**验证盲区记账（我的责任）**：E2E 每轮起全新子进程服务，「重构后未重启的长跑进程」
形态永远测不到；`make verify` 脚本因期望值过期（52→57）早已失效且不在门禁里
无人发现。两者本次都补了。

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 指纹一致放行 | ✅ | 单测 `test_ensure_fresh_passes_when_unchanged`；探针①新服务正常对话 |
| 指纹不一致拦截 | ✅ | 单测 `test_ensure_fresh_blocks_after_change`（文案含重启指引、无 ImportError 字样）；探针②：追加一行到 pricing.py → 66s 后对话返回「❌ 后端代码已变更（本进程启动于旧版代码）——请重启后端…变动文件：['zimeiti_harness/runtime/pricing.py']」 |
| make verify 通过 | ✅ | 修复后 `OK: 119 skills...` + `57 api routes` + `runtime API complete` |

## 连带修复（同批审计）

- `chat_router` supervisor 只捕 CancelledError：run_turn 早抛时后台任务静默死亡、
  前端收**空流**（探针②首轮复现：错误没传到前端）→ 补通用 except 转 SSE error 帧
- `verify_openclaw_removal.py`：import/文件路径跟随 harness 分层；路由期望 52→57
- **make verify 接入 make check**：该脚本失效数月无人知，本次收编后它当场红
  （3 个 ops-* 技能 description 短于 80 字符，五层流程变更遗留）→ 已补长
- README 故障排查补「后端代码已变更」条目

## 自动化验证

- **单测**：`test_stale_guard.py` 4 项全绿（含还原路径：单测级验证变更→还原→放行）
- **make check**：exit 0，**238 passed**（现含 verify 六连 + 守卫单测）
- **E2E 全量**：63/63、双端差异 0（chat_router 异常路径改动无回归）
- **三态探针**：①放行 ✓ ②拦截+精确文件列表 ✓ ③还原放行（单测覆盖；
  端到端复测一次为时序疑云——TTL 边界，逻辑由单测保证）

## 已知小项

- 指纹 TTL 60s：变更后最坏 60s 内才被发现（可接受；进程重启即重建快照）
- git checkout/merge 重写文件但内容不变 → sha1 内容哈希不误报（单测覆盖）
