---
comet_change: frontend-openclaw-debt
---

# 设计：前端 OpenClaw 语义残留清理

## 高层方案

纯前端重构，后端 SSE/API 契约不动：

```
现状（OpenClaw 残留）                      目标（deepagents 语义）
─────────────────────────────            ─────────────────────────────
打字机队列假设上游攒批，                  token 帧直渲染 + requestAnimationFrame
  队列慢消费造成渲染滞后        →           节流（合并同帧多 token）
重试只允许最后一轮                        移除本地限制：重试=POST 新一轮指令，
  （append-only 本地拦截）      →           会话重放语义由后端 checkpoint 决定
QuestionCards 经 ask_user RPC 桥  →      直连 SSE question 事件载荷 +
                                          POST /api/chat/question/answer
BroadcastChannel 会话防撞        →        保留，注释更新为现行理由（双开防撞），
  （注释还是 openclaw takeover）             不再提 takeover/flock
```

## 关键决策

### D1：不动 SSE 重连与游标
`?after=` 游标续传与自动重连机制现状工作良好且与运行时无关，明确排除在本 change 外（proposal Non-Goals）。

### D2：打字机保留节流而非删除
deepagents token 帧高频到达，逐字符写 DOM 会卡；保留合并渲染（每 ~50ms 批量 flush）——与「移除攒批假设」不矛盾：移除的是**语义依赖**（假设上游一次给一大段），保留的是**渲染性能手段**。

### D3：重试语义先验证后端行为
后端重试/续跑的实际行为（哪个端点、什么参数）在实现前用一次探针确认（起测试服务实测），避免把后端不支持的语义写进前端。若后端确实只支持特定重放形态，前端如实对齐并在 spec 场景中体现——以实测为准，不猜。

### D4：实施顺序
QuestionCards（最小、独立）→ 打字机 → 重试语义 → 注释清理。每步跑一次 S5 浏览器 E2E 兜底。

## 风险与对策

- **风险**：移除重试限制撞上后端真实限制 → 对策：D3 先实测；spec 场景写明「或被后端以明确理由拒绝时如实呈现」
- **风险**：打字机改坏现有流畅度 → 对策：每步 S5 回归；节流参数保守取现值

## Open Questions

无（D3 的实测属于实现期第一步，不阻塞设计）。
