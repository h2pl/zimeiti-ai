---
comet_change: wechat-bridge-scaffold
---

# Tasks：wechat-bridge-scaffold

## 1. Vendor 与合规

- [x] 1.1 vendor/openclaw-weixin（dist 原样 + LICENSE）+ NOTICE（来源/版本/MIT/未改动声明）+ 版本 pin 记录 <!-- comet-task:bc756bab-1908-4cce-87f6-e97d7ceb27b2 -->
- [x] 1.2 scripts/verify_wechat_vendor.py：vendor 哈希校验 + 合规三件套断言 + openclaw 引擎依赖扫描；接入 make check <!-- comet-task:9e708b3c-0497-4d36-a1a9-dce383eb519e -->

## 2. Shim 与宿主骨架

- [x] 2.1 shim/openclaw（account-id + config-mutation 两个 helper）+ package.json exports 解析 <!-- comet-task:cf17caf2-ce7f-477e-b0ae-dea97ce75be8 -->
- [x] 2.2 src/login.js（二维码登录+轮询+落盘）/ transport.js（可注入）/ bridge.js（骨架）/ sessions.js / index.js（CLI） <!-- comet-task:7cb5757a-a6ee-442e-8cdb-4cf8bbff0bdd -->

## 3. 验证与文档

- [x] 3.1 node:test 单测（shim 两 helper / 登录流程假 transport / 状态自检 / CLI 退出码） <!-- comet-task:0e8880c1-c04b-4129-b159-15a49ee93259 -->
- [x] 3.2 make check 全绿（含新 vendor 守卫）+ README 部署章节（Node 前提） <!-- comet-task:f0110dca-80e2-4f8e-a0ad-04b981a9e7ab -->
