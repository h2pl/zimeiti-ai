---
change: web-chat-publish
design-doc: openspec/changes/web-chat-publish/design.md
base-ref: 6cee62a
archived-with: 2026-10-10-web-chat-publish
---

<!-- comet-task-authority: openspec/changes/web-chat-publish/tasks.md -->

# 实施计划：web-chat-publish（对话工作台 + 发布中心）

决策见 design.md D1-D5。任务 T1-T9（comet-task-authority 指向 tasks.md）。

## 执行序（每项绑定 comet-task-ref）

<!-- comet-task-ref:57a1bacf-1878-4249-8d39-1c761e71af05 -->
<!-- comet-task-ref:57a1bacf-1878-4249-8d39-1c761e71af05 -->
- T1 runtime/chat.py 会话注册$

<!-- comet-task-ref:982a7d4c-c453-44fd-a070-e068255afc7a -->
<!-- comet-task-ref:982a7d4c-c453-44fd-a070-e068255afc7a -->
- T2 流式端点（astream 双模式 SSE）$

<!-- comet-task-ref:7bae93eb-3ef3-4be6-aa24-3ce7b99dfe71 -->
<!-- comet-task-ref:7bae93eb-3ef3-4be6-aa24-3ce7b99dfe71 -->
- T3 消息重建端点（aget_tuple）$

<!-- comet-task-ref:832d3ec0-e450-4038-9bdf-9df14b4f98a4 -->
<!-- comet-task-ref:832d3ec0-e450-4038-9bdf-9df14b4f98a4 -->
- T4 发布中心端点（enqueue 幂等 + list_entries）$

<!-- comet-task-ref:0aa91bcd-b0c4-4c32-9f6c-4cd814581c10 -->
<!-- comet-task-ref:0aa91bcd-b0c4-4c32-9f6c-4cd814581c10 -->
- T5 ChatPage（SSE 消费 + 内联问题卡）$

<!-- comet-task-ref:53fc5185-b6df-407d-9fa8-f4ca713f58a4 -->
<!-- comet-task-ref:53fc5185-b6df-407d-9fa8-f4ca713f58a4 -->
- T6 PublishCenterPage（入队 + 队列状态）$

<!-- comet-task-ref:e6976399-8716-433b-b0f8-703b641a6b79 -->
<!-- comet-task-ref:e6976399-8716-433b-b0f8-703b641a6b79 -->
- T7 导航接线（对话工作台/发布中心）$

<!-- comet-task-ref:395e9176-6dbb-4185-b015-b58686b3b672 -->
<!-- comet-task-ref:395e9176-6dbb-4185-b015-b58686b3b672 -->
- T8 make check + pnpm build$

<!-- comet-task-ref:93f836a7-97e2-4cce-82e7-ce13766b782f -->
<!-- comet-task-ref:93f836a7-97e2-4cce-82e7-ce13766b782f -->
- T9 端点冒烟 + spec 场景核对$
