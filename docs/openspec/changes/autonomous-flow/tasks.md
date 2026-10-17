---
comet_change: autonomous-flow
---

# Tasks：autonomous-flow

## 1. 包与持久化

- [ ] 1.1 建 `zimeiti_autonomous/`（flows/runner/store/router）；五层步骤枚举与裁剪校验 <!-- comet-task:5d41d363-aa40-4c4a-a6a1-ee9737e3affd -->
- [ ] 1.2 store 三表幂等建表（flows / flow_runs / flow_steps）+ CRUD 单测 <!-- comet-task:873f6b21-b809-4395-af20-1c54f8b31d52 -->

## 2. 编排执行与调度分发

- [ ] 2.1 runner 串行执行：逐步 prompt 组装（上一步摘要注入）+ 落记录 + 产出归档；单步失败即停 <!-- comet-task:b363ec57-9b8e-438b-b93d-f1211be54b59 -->
- [ ] 2.2 注入纪律：set_agent_entry（未注入显式报错）+ 包内不 import harness <!-- comet-task:fd8044e8-39dd-4328-af2e-61a20ecc4f7a -->
- [ ] 2.3 automations 扩展 kind=flow：scheduler 分发 + /api/flows 端点；既有 case/prompt 不回归 <!-- comet-task:20238ef8-9d25-4587-b97a-ca697fb1c402 -->

## 3. 验证

- [ ] 3.1 单测（裁剪校验/建表/逐步执行/失败即停/未注入报错）+ 端到端探针（mock 链路跑完整流程） <!-- comet-task:1e7568f6-542f-4cb5-91a7-e18a7a2143cd -->
- [ ] 3.2 make check 全绿 + E2E 63/63 不回归 <!-- comet-task:1cccd857-90bb-4da4-a3fb-e62ec00e96eb -->
