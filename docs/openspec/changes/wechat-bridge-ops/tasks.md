---
comet_change: wechat-bridge-ops
---

# Tasks：wechat-bridge-ops

## 1. 群聊与多账号

- [ ] 1.1 group.js：isGroupMessage/isBotMentioned/groupKey/stripMention（字段名全可配）+ dispatcher 接线（非@静默） <!-- comet-task:431e8b3c-928f-4683-bb0e-9ddb851c9f06 -->
- [ ] 1.2 index.js start 多账号并行（单账号隔离）+ status 全账号展示 <!-- comet-task:477fa86b-934f-4dec-a02c-c99fe223e6f4 -->

## 2. 开机自启

- [ ] 2.1 services/：systemd 单元 + launchd plist 模板 + install-service.sh（平台判别/填路径/enable+start） <!-- comet-task:4d34bbf0-d08c-4442-888c-a9469a813fee -->
- [ ] 2.2 Python 校验测试（单元内容关键项）+ README 联调校准说明 <!-- comet-task:a295ac6e-65ba-4c0f-ad66-c3649fa4ef71 -->

## 3. 验证

- [ ] 3.1 node:test（群判定/@检测/前缀/非@静默/多账号遍历）+ 探针扩展 + make check 全绿 <!-- comet-task:5fa39c2c-0526-4811-85d3-c8271229f645 -->
