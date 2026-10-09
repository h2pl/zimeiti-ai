---
change: real-account-verification
design-doc: openspec/changes/real-account-verification/design.md
base-ref: 9b234e374a1148b36b17870e8ec7dd4bfb825f92
---

<!-- comet-task-authority: openspec/changes/real-account-verification/tasks.md -->

# 实施计划：real-account-verification

验收义务履行：接线真实平台调用 + W1 读回三档 + 真账号走查 A3/A4/A6（频控 daily_limit=2）。
需求来源：PRD A3/A4/A6 ｜ 主规格 platform-publishing（MODIFIED 读回 + ADDED 登录态管理）｜ design D1-D5。

## Phase A 接线（1.1-1.5）

平台路由器（账号前缀→gzh API/xhs Playwright）→ 读回三档真实判定 → 扫码登录流程 → 占位钩子退役。
验收：路由/读回/登录单测全绿；生产路径 grep 无占位钩子。

## Phase B 真账号走查（2.1-2.5，需用户在场扫码）

全量回归 → gzh 草稿箱实测 → xhs 扫码发布实测 → 读回失败场景 → 频控边界。
验收：A3/A4/A6 逐条证据（审计 + 平台侧可见结果）。

## Phase C 收尾（3.1）

验证报告增补 + 缺陷记录。
