---
comet_change: agent-behavior-evals
---

# Tasks：agent 行为回归套件

## 1. 确定性层（进 make check）

- [ ] 1.1 `tests/evals/` 骨架 + conftest（端口/实例管理、用例清理、behavior 标记约定） <!-- comet-task:e511638b-55f0-43ac-bf54-529d1fe116c1 -->
- [ ] 1.2 契约段在位断言（执行偏向 / follow-through / ask-first / 记忆 / 五层索引 / 技能目录） <!-- comet-task:8435f1d9-0e9f-4802-8501-a26209014d06 -->
- [ ] 1.3 技能目录含既有详细技能断言（skill-topic-evaluator 等）+ 工具装配断言（exec_script / memory_* / ask_human 在册） <!-- comet-task:fcbd4ba7-1417-4b80-939e-60bd7e6ab9a0 -->
- [ ] 1.4 白名单拒绝 + fallback 判定矩阵断言（复用既有逻辑，补 4xx/5xx/429/连接错误四类） <!-- comet-task:fee480a9-d726-4bc4-8247-e5d0e3be3ec3 -->

## 2. 行为层（make evals，真实 LLM）

- [ ] 2.1 用例①：选题评估 → 路由到详细技能（工具轨迹含 read_file 命中 SKILL.md + 回复含评估结论） <!-- comet-task:b3d5dc20-b475-4f17-bbfa-7f181bf2c4d2 -->
- [ ] 2.2 用例②：付费生图 → 触发 ask_human 且不实际执行（双证据） <!-- comet-task:cb3e344a-7633-40e6-a88d-27af01773882 -->
- [ ] 2.3 用例③：清晰可逆任务 → 直执行不提问 <!-- comet-task:3348d410-0112-48b6-9740-498307797e3b -->
- [ ] 2.4 用例④：跨会话记忆 → 会话A 记录、会话B 检索命中并带溯源 <!-- comet-task:10a14805-ffd9-4fae-8216-2dfbee4dabf0 -->
- [ ] 2.5 用例⑤：fallback 切换 → 主模型坏端点，日志出现切换且回复正常 <!-- comet-task:8eae5e0a-f29f-422a-a820-ad16e30114dc -->
- [ ] 2.6 无密钥时整体 SKIP（退出码 0）+ 演示数据清理（finally） <!-- comet-task:553489fa-5c1a-4c6e-9469-4c0be29899a0 -->

## 3. 门禁接线

- [ ] 3.1 Makefile `evals` 目标；`check` 目标排除 behavior 标记 <!-- comet-task:a8f284df-20e4-4164-8491-cc2fe97cf397 -->
- [ ] 3.2 跑通：`make check`（含确定性层）+ `make evals`（五条全绿）双验 <!-- comet-task:60808f23-59c8-4af3-9b43-27825d529ea2 -->
