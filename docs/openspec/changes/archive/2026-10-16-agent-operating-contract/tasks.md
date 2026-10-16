---
comet_change: agent-operating-contract
---

# Tasks：操作契约层

## 1. 契约重构（agent_runtime）

- [x] 1.1 SYSTEM_PROMPT 重构：人格段 + 执行偏向 + Promised Work + ask-first 分级 + 编排 glue 纪律 + 五层索引（保留）+ 技能目录动态注入段（get_skills 渲染，按 layer 分组，name+description） <!-- comet-task:1a0b50d3-40c3-4087-852e-b5f303d6be6f -->
- [x] 1.2 技能目录注入带缓存（复用 get_skills 300s TTL；静态段在前动态段在后） <!-- comet-task:9339ed8d-f27c-4550-a994-d6cc7cf203b0 -->

## 2. ops-* 改路由层

- [x] 2.1 ops-discover → skill-trending-topics/skill-trend-rider（保留触发词+层职责） <!-- comet-task:a99f0dea-da5f-4b5b-bf82-fb7043c3babb -->
- [x] 2.2 ops-plan → skill-topic-evaluator <!-- comet-task:82531c47-7ab6-4908-bf79-b55a3bb64649 -->
- [x] 2.3 ops-create → copywriting + skill-quality-gate <!-- comet-task:a59db007-98b3-47ea-bf6c-390436fc881f -->
- [x] 2.4 ops-publish → skill-wechat-publisher + 发布门三步（content_guard → persona_gate 80 分线只提醒 → publish-log 留痕） <!-- comet-task:cf007ba9-a895-403e-be24-336a28d1a172 -->
- [x] 2.5 ops-review → skill-publish-analytics / skill-content-postmortem <!-- comet-task:99cc4cf6-42d4-4cd9-a126-3f6eda00239b -->

## 3. glue 脚本烟测

- [x] 3.1 manifest.py / calendar_ops.py / output_paths.py / persona_gate.py / publish-log 逐个烟测（存在且可运行）；不可用的在对应 ops 技能标注 <!-- comet-task:938fda43-1f1c-48ab-ad98-5e244343ca89 -->

## 4. 验证

- [x] 4.1 探针 A：选题评估任务 → 路由到 skill-topic-evaluator 且先读 SKILL.md <!-- comet-task:febb4b3f-dc54-4219-a28a-f68787cceaca -->
- [x] 4.2 探针 B：付费操作（生图）→ 触发 ask_human 确认而非直接执行 <!-- comet-task:ab6bba60-1894-4a64-89a9-34aa8437c57c -->
- [x] 4.3 探针 C：清晰可逆任务（读画像）→ 直接执行不索求许可 <!-- comet-task:857a2004-0230-440a-9121-b55d54bf0316 -->
- [x] 4.4 make check 全绿 + E2E S05 无回归 <!-- comet-task:3896b796-f873-452a-9f5a-9ff9f78ec673 -->
