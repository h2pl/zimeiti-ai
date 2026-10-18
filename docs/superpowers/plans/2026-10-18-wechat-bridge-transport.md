---
change: wechat-bridge-transport
design-doc: docs/openspec/changes/wechat-bridge-transport/design.md
base-ref: a065d3e
archived-with: 2026-10-18-wechat-bridge-transport
---

# Plan：微信消息 ↔ zimeiti agent 桥接

<!-- comet-task-authority: docs/openspec/changes/wechat-bridge-transport/tasks.md -->

## G1 客户端与分发 <!-- comet-task-ref:7e88209f-d4b3-4a30-b580-41a836fd7ee8 --><!-- comet-task-ref:756a784d-fb9e-4448-b178-06c64b81e7e3 -->

zimeiti-client（SSE 读全文 + 错误翻译）；dispatcher（指令/串行锁/typing/分段）。

## G2 start 与探针 <!-- comet-task-ref:30205772-cef0-4b9a-bd5e-ed31461efcc4 --><!-- comet-task-ref:05fe5e6c-7f72-4fe7-a4b8-d3c4d9664554 -->

start 命令落地（登录态/连通性/优雅停机）；探针（真实 zimeiti + 假 ilink）。

## G3 验证 <!-- comet-task-ref:7c765405-98a6-4a05-9fe1-b9f73e701619 --><!-- comet-task-ref:7028d90f-6209-461e-a62a-58e937b5c675 -->

node:test 15/15；探针 PASS；make check 278 passed；E2E 69/69。
