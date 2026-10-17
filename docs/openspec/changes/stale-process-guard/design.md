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
