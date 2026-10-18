---
comet_change: wechat-bridge-transport
---

# Tasks：wechat-bridge-transport

## 1. 客户端与分发

- [x] 1.1 zimeiti-client.js：chat（SSE 读全文 + activity 回调 + error 透传 + 超时）+ ping；单测（本地 SSE 服务器） <!-- comet-task:7e88209f-d4b3-4a30-b580-41a836fd7ee8 -->
- [x] 1.2 dispatcher.js：指令识别 + 每用户串行锁 + typing 先行 + 分段回发 + 错误如实翻译 <!-- comet-task:756a784d-fb9e-4448-b178-06c64b81e7e3 -->

## 2. start 命令与探针

- [x] 2.1 index.js start 落地（登录态检查 → bridge 装配 onMessage → 状态展示） <!-- comet-task:30205772-cef0-4b9a-bd5e-ed31461efcc4 -->
- [x] 2.2 探针 probe_wechat_bridge.py：真实 zimeiti（mock LLM）+ 假 ilink transport，断言闭环与会话 id；README 联调步骤 <!-- comet-task:05fe5e6c-7f72-4fe7-a4b8-d3c4d9664554 -->

## 3. 验证

- [x] 3.1 node:test 全量（客户端/分发/锁/分段/错误路径）+ make check 全绿 <!-- comet-task:7c765405-98a6-4a05-9fe1-b9f73e701619 -->
- [x] 3.2 探针 PASS + CLI status 展示连通性 <!-- comet-task:7028d90f-6209-461e-a62a-58e937b5c675 -->
