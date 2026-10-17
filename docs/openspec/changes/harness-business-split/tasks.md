---
comet_change: harness-business-split
---

# Tasks：harness/business 分层

## 1. 包落位与依赖倒置

- [ ] 1.1 建 `zimeiti_harness/`：git mv runtime 五模块 + memory/ + usage.py；contract.py 注入点 <!-- comet-task:e281761b-f2a2-4763-b469-83df3408076a -->
- [ ] 1.2 agent_runtime._skills_catalog 改走 contract；删 content import <!-- comet-task:159be7ae-7493-4ff6-bf6f-eb24bc1f3d9c -->
- [ ] 1.3 chat.py/status.py 归位 zimeiti_api/chat_router.py、status_router.py；app.py 更新 <!-- comet-task:7a042994-ee11-4c91-87ae-ce17130c6e53 -->

## 2. 注入与守卫

- [ ] 2.1 scheduler set_ask_sync 注入；删函数级硬 import；app.py 接线 <!-- comet-task:a3ad1618-d8bb-458c-b0d9-ba5575e41724 -->
- [ ] 2.2 分层守卫确定性测试（扫描 harness 源码禁业务域 import，core 白名单） <!-- comet-task:f5b20336-9ead-4da4-b58e-2da55c24114c -->
- [ ] 2.3 pyproject/mypy/ruff/bandit/Makefile 范围同步；全库 import 更新（13 文件） <!-- comet-task:28c2fda5-d03d-4fe9-bd2e-e9446256d596 -->

## 3. 验证

- [ ] 3.1 make check 全绿 + 分层守卫在册；make evals 5/5 <!-- comet-task:8c685111-1104-46c6-99d6-6f87b3fc3e65 -->
- [ ] 3.2 E2E 全量 63/63；对话/结构化/自动化探针行为一致 <!-- comet-task:a1d4f40a-b2ad-45a1-b9d9-2a461c3068e4 -->
