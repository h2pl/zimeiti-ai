# Tasks

## 1. 真实平台接线

- [x] 1.1 平台路由器：按账号名前缀路由 gzh/xhs 平台调用；验证：单测断言 gzh-main→GzhClient、xhs-main→XhsPublisher <!-- comet-task:b936b77f-ffd9-48b4-8f2e-8214b305c2d7 -->
- [x] 1.2 公众号读回对账：draft/count+list 匹配标题 → 三档；验证：单测（mock 响应）三档各一 <!-- comet-task:166f1fdf-eec4-4783-8353-f80d756c6338 -->
- [x] 1.3 小红书发布+读回：创作者中心笔记列表解析 → 三档；验证：FakePage 单测 <!-- comet-task:7af24f4f-5bf5-4a3b-a69f-918eba02425e -->
- [x] 1.4 小红书扫码登录流程（storage_state 持久化/复用/失效引导）；验证：FakePage 单测流程断言 <!-- comet-task:c8e966bf-8198-4627-92ee-9afb3b83afe9 -->
- [x] 1.5 W1 回归：占位钩子仅保留单测路径，生产路径不再触达；验证：grep + 单测 <!-- comet-task:c5dd86c4-2439-422a-b7cd-f5cfd69fe3ab -->

## 2. 端到端与真账号验收

- [x] 2.1 全量测试回归（现有 32 + 新增）；验证：check-api.sh 全绿 <!-- comet-task:ed38fb2e-fcaf-4338-a54d-9ae8977a3577 -->
  - 证据（2026-10-09）：make check 两次全绿——vendor 化后 47 passed / cov 86.35%（commit c6d0c92、657dbc1）；app.py 硬编码修复后 47 passed / cov 86%（见 2.6）
- [x] 2.2 真账号走查 A3：gzh 草稿箱上传 + 读回 verified（日限内）；验证：审计+平台截图 <!-- comet-task:bf4a10de-84ba-4abb-ad85-2c21c40a7e32 -->
- [x] 2.3 真账号走查 A3：xhs 扫码登录 + 发布 + 读回 verified；验证：同上 <!-- comet-task:563dfc99-f265-4318-ac4f-6aed8e7505d6 -->
  - 证据（2026-10-09）：scripts/walkthrough_a3_xhs.py——xiaohongshu-mcp（xpzouying，v2.5.5，API 路线）私密发布「仅自己可见」+ 笔记管理读回 verified，审计 published 留痕
  - 方案演进：edith API 逆向（风控拒签名+假阳性 success）→ 自研 DOM（站点改版频繁）→ 复用成熟开源 xiaohongshu-mcp 本地服务（含 Tiptap 适配/拟人化/URL 跳离判定），XhsPublisher 改为其 API 客户端
  - 踩坑入库：话题含空格联想超时（客户端过滤）；litellm 残留事件循环致 sync Playwright 冲突（读回走子进程 xhs_readback.py）；web 草稿箱为浏览器本地无产品价值
- [x] 2.4 真账号走查 A4：人为制造读回失败场景 → unverified 留痕；验证：审计记录 <!-- comet-task:04bd800a-0db2-4b20-87cc-143570f31d6a -->
  - 证据（2026-10-09）：scripts/walkthrough_a4_readback_failure.py——真实草稿箱上传后篡改标题读回 → unverified，正确标题 → verified；审计 JSONL action=published outcome=unverified（drill=a4_readback_failure）
- [x] 2.5 走查 A6：频控边界验证（日限 2 篇后第三篇被拒）；验证：审计记录 <!-- comet-task:c1c1ee7a-2128-4e1c-b07b-cfcff64a8ad5 -->
  - 证据（2026-10-09）：scripts/walkthrough_a5_rate_limit.py——2 篇真实上传 verified，第三篇 RateLimitExceeded 且平台零调用（草稿数 247→247）；审计 publish_failed 留痕
  - 缺陷修复：A5 演练暴露 executor.publish 硬编码 readback=unverified（生产审计永远 unverified，W1 复发）→ 已透传路由器三档 outcome + 2 个回归单测（test_publisher.py）
- [x] 2.6 遗留修复：审批端点 profile 硬编码 xhs-main → pending 记录 account，恢复端点按记录加载画像（gzh 接入 API 审批前置项，归档 design ①）；验证：test_approvals_api spy 断言 loaded_accounts

## 3. 收尾

- [ ] 3.1 测试报告与缺陷记录更新（verify report 增补）；验证：文档存在且与证据一致 <!-- comet-task:4951b428-40ed-4bda-8c9d-99fcf0d5d984 -->
