---
comet_change: frontend-openclaw-debt
---

# Tasks：前端 OpenClaw 语义残留清理

## 1. 探针

- [x] 1.1 后端重试/续跑行为实测：起测试服务，对历史轮次发起重试请求，记录真实端点/参数/响应（结果回填 design D3 结论） <!-- comet-task:7e436461-d24f-45be-839e-84489b3705ca -->

## 2. QuestionCards 直连

- [x] 2.1 QuestionCards 组件改为直消费 SSE question 事件载荷 → POST /api/chat/question/answer；移除 ask_user RPC 桥语义与对应代码 <!-- comet-task:af9b1cfb-6ebd-4021-9a6f-2728549ddf80 -->
- [x] 2.2 S5 浏览器 E2E 回归 <!-- comet-task:5e04b3da-4e4c-4d0e-b720-9ce245d2a3e4 -->

## 3. 打字机渲染

- [x] 3.1 移除「上游攒批」假设：token 帧直渲染 + rAF/定时合并节流（每 ~50ms flush）；删除对应队列消费逻辑与过时注释 <!-- comet-task:fdc28792-328c-4a1c-bacf-541fff379679 -->
- [x] 3.2 S5 回归（长回复渲染流畅度人工核对） <!-- comet-task:411e2eba-7494-4cdf-8249-cf94f85b5a0e -->

## 4. 重试语义

- [x] 4.1 按 1.1 实测结论对齐重试逻辑：移除「仅最后一轮」本地拦截，保留后端明确拒绝时的如实呈现 <!-- comet-task:e4d30db9-ff95-419a-ae12-226d255ef3d4 -->
- [x] 4.2 S5 回归 <!-- comet-task:ab754b15-4e94-4c2e-85c5-b142baaa1c3d -->

## 5. 收尾

- [x] 5.1 全局清理 OpenClaw 残留注释/命名（保留机制更新现行理由注释，如 BroadcastChannel 双开防撞） <!-- comet-task:d21f92ec-dc31-4b8c-bccb-a33e93c1ca11 -->
- [x] 5.2 `make check` 全绿 + tsc 通过 <!-- comet-task:dd919cff-12c3-49bd-ba11-31df3a786fb2 -->
- [x] 5.3 spec 四条 Requirement 的 Scenario 逐条对照 <!-- comet-task:1ee74603-8390-40ef-b0bf-0b303bed4462 -->
