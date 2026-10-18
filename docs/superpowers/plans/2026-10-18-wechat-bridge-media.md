---
change: wechat-bridge-media
design-doc: docs/openspec/changes/wechat-bridge-media/design.md
base-ref: 967d07d
---

# Plan：微信媒体收发

<!-- comet-task-authority: docs/openspec/changes/wechat-bridge-media/tasks.md -->

## G1 媒体模块与接线 <!-- comet-task-ref:1c0abb3d-6b4b-492d-a715-0e66cc89a2d8 --><!-- comet-task-ref:7bfd27e1-21c0-4292-8c12-5129516048dd -->

media.js（提取/落盘/指令解析/vendor 惰性加载）；dispatcher 双向接线。

## G2 验证 <!-- comet-task-ref:2bd7054f-b8a3-471f-9b96-27205895849f --><!-- comet-task-ref:a8d935a3-b768-4232-b7c3-a75a4bb09129 -->

node:test 24/24；媒体探针 PASS；make check 278 passed；vendor 守卫 PASS。
