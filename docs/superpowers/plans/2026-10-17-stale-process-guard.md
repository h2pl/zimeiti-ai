---
change: stale-process-guard
design-doc: docs/openspec/changes/stale-process-guard/design.md
base-ref: 4b22b4c
archived-with: 2026-10-17-stale-process-guard
---

# Plan：stale-process-guard

<!-- comet-task-authority: docs/openspec/changes/stale-process-guard/tasks.md -->

## G1 指纹守卫 <!-- comet-task-ref:22de58ff-24e8-4f7e-bad3-f122c953b92e --><!-- comet-task-ref:82817e79-fa20-4949-84be-0650f28f1c7a --><!-- comet-task-ref:e4a97bd0-d166-4139-b13c-cba3916c39a1 -->

fingerprint.py（sha1 内容哈希+60s TTL）+ 四入口接入 + lifespan capture；
单测（放行/拦截文案/哈希稳定/双包覆盖）。

## G2 verify 收编与文档 <!-- comet-task-ref:55b3a76f-515e-497f-9d6e-189efc1c5319 --><!-- comet-task-ref:47f4c269-5ea5-4bc8-872e-d3c4bbc501a3 -->

verify 脚本路径/期望修复；make verify 接入 make check；README 故障排查。

## G3 验证 <!-- comet-task-ref:5667c6a5-492b-44ab-8ccf-e67820c91558 --><!-- comet-task-ref:d7ce56c6-cc52-42ca-a487-3cfb6e993151 -->

make check 238 passed（含 verify+守卫单测）；三态探针；E2E 63/63。
