# 任务：web-chat-publish

## 1. 后端

- [ ] T1 `runtime/chat.py`：会话注册（create/list/registry 持久化）+ 测试
- [ ] T2 流式端点：`POST /api/chat/sessions/{tid}/stream`（astream messages
      增量 + interrupt 帧 + done/error 帧）+ 测试（fake agent）
- [ ] T3 `GET /api/chat/sessions/{tid}/messages`（checkpointer state 重建）+ 测试
- [ ] T4 发布中心端点：enqueue（幂等复用 publish_queue）+ 队列列表 + 测试

## 2. 前端

- [ ] T5 ChatPage：会话列表+消息流+SSE 消费+内联问题卡
- [ ] T6 PublishPage：内容库草稿选择+入队+队列状态
- [ ] T7 导航接线（Chat/发布中心）+ pnpm build

## 3. 验证

- [ ] T8 make check + pnpm build
- [ ] T9 端点冒烟 + spec 场景核对
