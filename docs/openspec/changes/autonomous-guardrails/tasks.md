---
comet_change: autonomous-guardrails
---

# Tasks：autonomous-guardrails

## 1. 护栏实现

- [ ] 1.1 步骤级重试（可重试判定：配置性错误不重试）+ 退避；重试次数落步骤记录 <!-- comet-task:f47a61bb-7554-41b7-9ef8-1a531239244f -->
- [ ] 1.2 连续失败熔断（达阈值自动停用 + 原因持久化；成功后归零） <!-- comet-task:c6588c95-6505-4388-8b00-7713bcb963b9 -->
- [ ] 1.3 预算护栏（当日累计 cost_usd 比对上限；无单价放行不拦截） <!-- comet-task:3bb913d8-0140-4135-b339-91756501af0b -->

## 2. 自主模式 HITL 策略

- [ ] 2.1 AutonomyPolicy：付费/发布/不可逆 → blocked（待确认，不阻塞）+ 继续后续步骤 <!-- comet-task:4dbe9de5-2332-4217-830f-ab5bc4671ee4 -->
- [ ] 2.2 runner 接入护栏（配置驱动，默认开可关）+ GET /api/autonomous/status <!-- comet-task:96073699-9e18-4565-9f60-dd56a3f9dc10 -->

## 3. 验证

- [ ] 3.1 单测（重试/不重试配置错/熔断/成功后归零/超预算即停/无单价放行/blocked 不阻塞）+ 探针 <!-- comet-task:b713d152-5e7b-448b-a4e3-590838037ede -->
- [ ] 3.2 make check 全绿 + E2E 63/63 不回归 <!-- comet-task:fb033616-11c1-4c68-ae23-6a0e1f4a92b9 -->
