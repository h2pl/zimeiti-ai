---
comet_change: autonomous-feedback
---

# Tasks：autonomous-feedback

## 1. 汇总与校准

- [x] 1.1 feedback.collect_published：读 outputs/_analytics，按平台/时间窗聚合；源缺失或坏 JSON → 空列表不报错 <!-- comet-task:103b7118-0aa9-430a-9ee0-4ee2630f1090 -->
- [x] 1.2 build_calibration：事实 → 校准信号（只陈述事实与缺口，无数据如实报告）+ 归档 outputs/_feedback/<date>.md <!-- comet-task:b003fba7-53aa-40b6-b8bf-cbbd86ada65e -->

## 2. 注入发现层

- [x] 2.1 flows.build_step_prompt 支持 feedback 段（仅 discover 注入）+ runner 在 discover 步调用（可关闭） <!-- comet-task:4cc3ef81-799f-43a5-adf9-cd3c5acb2cba -->
- [x] 2.2 GET /api/feedback 暴露最近校准信号 <!-- comet-task:cf220eb1-c7f1-45d3-8679-52503649fc03 -->

## 3. 验证

- [x] 3.1 单测（有事实汇总/无事实降级/坏文件容错/仅 discover 注入/归档落盘）+ 探针（造样本→跑流程→断言校准段） <!-- comet-task:9ef31df4-dc51-40f3-afdf-9fb281e4bdb8 -->
- [x] 3.2 make check 全绿 + E2E 63/63 不回归 <!-- comet-task:6532348a-848e-4d38-a2d1-3dd4453ebe13 -->
