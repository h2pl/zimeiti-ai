---
change: wechat-bridge-scaffold
design-doc: docs/openspec/changes/wechat-bridge-scaffold/design.md
base-ref: 08fc4f9
archived-with: 2026-10-18-wechat-bridge-scaffold
---

# Plan：微信桥 scaffold

<!-- comet-task-authority: docs/openspec/changes/wechat-bridge-scaffold/tasks.md -->

## G1 Vendor 与合规 <!-- comet-task-ref:bc756bab-1908-4cce-87f6-e97d7ceb27b2 --><!-- comet-task-ref:9e708b3c-0497-4d36-a1a9-dce383eb519e -->

协议码原样收录 + MANIFEST 哈希 + NOTICE；verify_wechat_vendor.py 三断言
（合规/完整性/零 openclaw 引擎依赖）接入 make check。

## G2 Shim 与宿主 <!-- comet-task-ref:cf17caf2-ce7f-477e-b0ae-dea97ce75be8 --><!-- comet-task-ref:7cb5757a-a6ee-442e-8cdb-4cf8bbff0bdd -->

3 个 helper shim（temp-path/account-id/config-mutation，可达面取证得出）；
login/transport/bridge/sessions/CLI 骨架。

## G3 验证 <!-- comet-task-ref:0e8880c1-c04b-4129-b159-15a49ee93259 --><!-- comet-task-ref:f0110dca-80e2-4f8e-a0ad-04b981a9e7ab -->

node:test 6/6；CLI 冒烟退出码契约；make check 278 passed；E2E 69/69 不回归。
