# Brainstorm Summary

- Change: mvp-scaffold
- Date: 2026-10-08

## Confirmed Technical Approach

- 引擎：deepagents>=0.7.6（LangGraph 底座），D0-D7 决策已获用户确认（design.md）
- T2 选题信源（已确认）：公益热搜 API + 用户手动方向 双通道
- T3 审批通知（已确认）：仅 Web 审批页（apps/web），无 IM/邮件推送
- 测试策略：pytest 单元（闸门/频控/对账/画像校验）+ 集成（真库 interrupt-resume）+ 真账号小流量验收 A1-A6
- Spec Patch：无（5 个 delta spec 已覆盖 PRD A1-A6）

## T1 拓扑（已确认 2026-10-08）

- 双形态共用同一套 agent 资产（tools/subagents/interrupt_on/checkpointer）
- 工作台形态：用户 Web/对话逐环节驱动，主 agent 直操（Easel 式交互）
- 托管形态：定时/事件触发，主 agent 编排 + 创作 subagent 委派（xiaobei 式）+ 审批 interrupt 阻断
- 设计确认：整体技术方案已批准（Step 1c）

## Key Tradeoffs and Risks

- 小红书/公众号 Playwright 自动化风控风险 → 频控+读回对账+测试号小流量
- 公益热搜 API 无 SLA → 商业阶段换自建源（已记录）
- 双形态并行前端成本 → 首版 Web 仅审批+状态最小界面

## Test Strategy

pytest 单元 + docker 真库集成（interrupt-resume）+ 真账号小流量验收（A1-A6）

## Spec Patch

None
