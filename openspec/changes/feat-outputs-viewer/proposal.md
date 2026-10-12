# 提案：内容库正文查看器（feat-outputs-viewer）

## Why

对齐缺口矩阵（docs/prd/reference-gap-analysis.md）⚠ 档第 5 项：OutputsPage
只有元数据列表，Easel 可查看文章正文并可单篇发布。正文查看是发布编排
（下一变更）的前置：看不到内容就无法决定是否发布。

## What Changes

- 后端：`GET /api/outputs/{account}/{slug}`——返回 slug 元数据 + 双平台草稿
  正文（title/body/tags）+ 合规结论（只读，无新写路径）
- 前端：OutputsPage 行点击 → 侧滑查看器（标题/元信息/正文渲染/合规徽章），
  复用 marked+DOMPurify 渲染 markdown
- 无既有端点行为变更

## Capabilities

- **Modified Capabilities**: `web-workbench`（ADDED：内容查看器需求）

## Non-Goals

- 正文编辑（内容产出后不改，改走重新创作）
- 单篇发布按钮（下一变更 feat-publish-orchestration）

## 关键决策

- 正文渲染复用 BreakdownPage 已引入的 marked+DOMPurify（不新增依赖）
- 端点读 drafts.json 全文（D5 只读扫描约束的例外：明确为查看器端点，
  仍限 account/slug 白名单防路径遍历）
