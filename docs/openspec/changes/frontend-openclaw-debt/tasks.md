---
comet_change: frontend-openclaw-debt
---

# Tasks：前端 OpenClaw 语义残留清理

## 1. 探针

- [ ] 1.1 后端重试/续跑行为实测：起测试服务，对历史轮次发起重试请求，记录真实端点/参数/响应（结果回填 design D3 结论）

## 2. QuestionCards 直连

- [ ] 2.1 QuestionCards 组件改为直消费 SSE question 事件载荷 → POST /api/chat/question/answer；移除 ask_user RPC 桥语义与对应代码
- [ ] 2.2 S5 浏览器 E2E 回归

## 3. 打字机渲染

- [ ] 3.1 移除「上游攒批」假设：token 帧直渲染 + rAF/定时合并节流（每 ~50ms flush）；删除对应队列消费逻辑与过时注释
- [ ] 3.2 S5 回归（长回复渲染流畅度人工核对）

## 4. 重试语义

- [ ] 4.1 按 1.1 实测结论对齐重试逻辑：移除「仅最后一轮」本地拦截，保留后端明确拒绝时的如实呈现
- [ ] 4.2 S5 回归

## 5. 收尾

- [ ] 5.1 全局清理 OpenClaw 残留注释/命名（保留机制更新现行理由注释，如 BroadcastChannel 双开防撞）
- [ ] 5.2 `make check` 全绿 + tsc 通过
- [ ] 5.3 spec 四条 Requirement 的 Scenario 逐条对照
