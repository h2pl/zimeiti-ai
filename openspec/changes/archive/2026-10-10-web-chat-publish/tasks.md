# 任务：web-chat-publish

## 1. 后端

- [x] T1 `runtime/chat.py`：会话注册（create/list/registry 持久化）+ 测试 <!-- comet-task:57a1bacf-1878-4249-8d39-1c761e71af05 -->
- [x] T2 流式端点：`POST /api/chat/sessions/{tid}/stream`（astream messages <!-- comet-task:982a7d4c-c453-44fd-a070-e068255afc7a -->
      增量 + interrupt 帧 + done/error 帧）+ 测试（fake agent）
- [x] T3 `GET /api/chat/sessions/{tid}/messages`（checkpointer state 重建）+ 测试 <!-- comet-task:7bae93eb-3ef3-4be6-aa24-3ce7b99dfe71 -->
- [x] T4 发布中心端点：enqueue（幂等复用 publish_queue）+ 队列列表 + 测试 <!-- comet-task:832d3ec0-e450-4038-9bdf-9df14b4f98a4 -->

## 2. 前端

- [x] T5 ChatPage：会话列表+消息流+SSE 消费+内联问题卡 <!-- comet-task:0aa91bcd-b0c4-4c32-9f6c-4cd814581c10 -->
- [x] T6 PublishPage：内容库草稿选择+入队+队列状态 <!-- comet-task:53fc5185-b6df-407d-9fa8-f4ca713f58a4 -->
- [x] T7 导航接线（Chat/发布中心）+ pnpm build <!-- comet-task:e6976399-8716-433b-b0f8-703b641a6b79 -->

## 3. 验证

- [x] T8 make check + pnpm build <!-- comet-task:395e9176-6dbb-4185-b015-b58686b3b672 -->
- [x] T9 端点冒烟 + spec 场景核对 <!-- comet-task:93f836a7-97e2-4cce-82e7-ce13766b782f -->
