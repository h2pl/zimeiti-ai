---
comet_change: wechat-bridge-media
---

# Tasks：wechat-bridge-media

## 1. 媒体模块

- [ ] 1.1 media.js：extractMediaItems / saveInboundMedia（下载器注入）/ parseMediaDirectives（独占行约定） <!-- comet-task:1c0abb3d-6b4b-492d-a715-0e66cc89a2d8 -->
- [ ] 1.2 dispatcher 接线：入站落盘+附注、出站 MEDIA 回发（发送器注入）；语音 silk 如实标注 <!-- comet-task:7bfd27e1-21c0-4292-8c12-5129516048dd -->

## 2. 验证

- [ ] 2.1 node:test：提取/落盘（含失败隔离）/指令解析（独占行/路径保真/MEDIA 行剥离）/dispatcher 双向接线 <!-- comet-task:2bd7054f-b8a3-471f-9b96-27205895849f -->
- [ ] 2.2 探针扩展：入站图片（假下载器）+ 出站 MEDIA（假发送器）；make check 全绿 <!-- comet-task:a8d935a3-b768-4232-b7c3-a75a4bb09129 -->
