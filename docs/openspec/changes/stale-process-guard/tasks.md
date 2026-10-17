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
