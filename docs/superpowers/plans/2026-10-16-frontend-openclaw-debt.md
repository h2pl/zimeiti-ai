---
change: frontend-openclaw-debt
design-doc: docs/openspec/changes/frontend-openclaw-debt/design.md
base-ref: 9c4b05b
archived-with: 2026-10-16-frontend-openclaw-debt
---

# Plan：frontend-openclaw-debt 前端 OpenClaw 语义残留清理

<!-- comet-task-authority: docs/openspec/changes/frontend-openclaw-debt/tasks.md -->

## G1 探针：后端重试行为实测 <!-- comet-task-ref:7e436461-d24f-45be-839e-84489b3705ca -->

起测试服务，对历史轮次发起重试请求（chat/stream 带重试指令形态），记录端点/参数/响应。

## G2 QuestionCards 直连 <!-- comet-task-ref:af9b1cfb-6ebd-4021-9a6f-2728549ddf80 --><!-- comet-task-ref:5e04b3da-4e4c-4d0e-b720-9ce245d2a3e4 -->

QuestionCards 改直消费 SSE question 事件载荷 → POST /api/chat/question/answer；删 RPC 桥语义；S05 回归。

## G3 打字机渲染 <!-- comet-task-ref:fdc28792-328c-4a1c-bacf-541fff379679 --><!-- comet-task-ref:411e2eba-7494-4cdf-8249-cf94f85b5a0e -->

App.tsx 移除「上游攒批」假设：token 帧直渲染 + rAF 节流合并；删队列消费逻辑与过时注释；S05 回归。

## G4 重试语义 <!-- comet-task-ref:e4d30db9-ff95-419a-ae12-226d255ef3d4 --><!-- comet-task-ref:ab754b15-4e94-4c2e-85c5-b142baaa1c3d -->

按 G1 实测对齐：移除「仅最后一轮」本地拦截，保留后端拒绝时的如实呈现；S05 回归。

## G5 收尾 <!-- comet-task-ref:d21f92ec-dc31-4b8c-bccb-a33e93c1ca11 --><!-- comet-task-ref:dd919cff-12c3-49bd-ba11-31df3a786fb2 --><!-- comet-task-ref:1ee74603-8390-40ef-b0bf-0b303bed4462 -->

OpenClaw 残留注释/命名清理（BroadcastChannel 保留+更新理由）；make check + tsc；spec 场景逐条核对。
