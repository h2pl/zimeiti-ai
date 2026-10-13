---
archived-with: 2026-10-13-phase1-deepagents-runtime
status: final
---


<!-- 任务 ID 映射 -->
<!-- comet-task-ref:284fe45b-d03f-453b-944b-0f59ced25bbb --> 1.1 新增 `apps/api/easel/agent_runtime.py`：会话落盘、模型工厂、`create_deep_agent`（ask_human HITL）、流式 run_turn、resume、pending question 存储
<!-- comet-task-ref:a7ff06ba-755b-49e7-9214-252aaedc9524 --> 1.2 安装 langchain-openai；验证模块导入
<!-- comet-task-ref:1af3089e-f562-41ca-9eff-b846a7926f6c --> 2.1 `/api/chat/stream` supervisor 顶部按 ZIMEITI_RUNTIME 分支到运行时（默认 deepagents）
<!-- comet-task-ref:4815fbd8-3841-440b-a004-07cb85b478bc --> 2.2 `/api/chat/question/answer` 与 `/api/chat/question/status` 运行时模式短路
<!-- comet-task-ref:dbce454a-24c1-4d51-bd8a-a8f256b29e95 --> 2.3 验证：`import app` 成功、66 条路由不变
<!-- comet-task-ref:22a3830e-77ee-4dd4-84d8-2f10e06f5869 --> 3.1 服务重启，`/api/status` 200
<!-- comet-task-ref:630d3dde-0c4e-485f-b686-22bf88a12be8 --> 3.2 冒烟：POST /api/chat/stream 返回 activity/error（无 key 降级）/done 帧，HTTP 200 无崩溃
<!-- comet-task-ref:21676720-e45e-4cf7-9186-5900374cfa95 --> 3.3 验证：SSE 帧格式符合前端契约（done 携带 sessionKey）
