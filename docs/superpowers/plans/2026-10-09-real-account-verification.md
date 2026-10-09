---
change: real-account-verification
design-doc: openspec/changes/real-account-verification/design.md
base-ref: 9b234e374a1148b36b17870e8ec7dd4bfb825f92
archived-with: 2026-10-09-real-account-verification
---

<!-- comet-task-authority: openspec/changes/real-account-verification/tasks.md -->

# 实施计划：real-account-verification

验收义务履行：接线真实平台调用 + W1 读回三档 + 真账号走查 A3/A4/A6（频控 daily_limit=2）。
需求来源：PRD A3/A4/A6 ｜ 主规格 platform-publishing（MODIFIED 读回 + ADDED 登录态管理）｜ design D1-D5。

## Phase A 接线（任务 1.1-1.5）

平台路由器（账号前缀→gzh API/xhs）→ 读回三档真实判定 → 扫码登录流程 → 占位钩子退役。
验收：路由/读回/登录单测全绿；生产路径 grep 无占位钩子。

## Phase B 真账号走查（任务 2.1-2.6，需真实账号/用户在场）

全量回归 → gzh 草稿箱实测 → xhs 发布实测 → 读回失败场景 → 频控边界 → 遗留修复。
验收：A3/A4/A6 逐条证据（审计 + 平台侧可见结果）。

## Phase C 收尾（任务 3.1）

验证报告增补 + 缺陷记录。

## 任务引用（canonical refs）

<!-- comet-task-ref:b936b77f-ffd9-48b4-8f2e-8214b305c2d7 -->
<!-- comet-task-ref:166f1fdf-eec4-4783-8353-f80d756c6338 -->
<!-- comet-task-ref:7af24f4f-5bf5-4a3b-a69f-918eba02425e -->
<!-- comet-task-ref:c8e966bf-8198-4627-92ee-9afb3b83afe9 -->
<!-- comet-task-ref:c5dd86c4-2439-422a-b7cd-f5cfd69fe3ab -->
<!-- comet-task-ref:ed38fb2e-fcaf-4338-a54d-9ae8977a3577 -->
<!-- comet-task-ref:bf4a10de-84ba-4abb-ad85-2c21c40a7e32 -->
<!-- comet-task-ref:563dfc99-f265-4318-ac4f-6aed8e7505d6 -->
<!-- comet-task-ref:04bd800a-0db2-4b20-87cc-143570f31d6a -->
<!-- comet-task-ref:c1c1ee7a-2128-4e1c-b07b-cfcff64a8ad5 -->
<!-- comet-task-ref:cd818919-de53-49aa-bf96-a7b9627aa2b7 -->
<!-- comet-task-ref:4951b428-40ed-4bda-8c9d-99fcf0d5d984 -->
