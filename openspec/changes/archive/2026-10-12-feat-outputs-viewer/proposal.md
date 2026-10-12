# 提案：内容库正文查看（feat-outputs-viewer）

## Why

对齐缺口矩阵 ⚠ 第 5 项：OutputsPage 只有元数据列表；Easel 可查看文章正文
（并单篇发布，发布已由发布中心承接）。当前产物正文只存在于磁盘
drafts.json/cover.png，Web 不可见。

## What Changes

- 后端：`GET /api/outputs/{account}/{slug}`：返回单篇产物全文
  （topic/topic_direction/compliance/drafts 全文 + created_at）；
  account/slug 白名单（防路径遍历）；404 兜底
- 前端 OutputsPage：条目可展开正文（xhs/gzh 两平台标题正文+封面图）；
  封面图经 `GET /api/outputs/{account}/{slug}/cover.png` FileResponse

## Capabilities

- **Modified Capabilities**: `web-workbench`（ADDED：内容库正文查看需求）

## Non-Goals

- 不做正文编辑（编辑=重新创作，走对话工作台）
- 封面图上传/裁剪 UI（已由后端发布链路处理）

## 关键决策

- 封面图直接 FileResponse（内容库只读视图，不引入静态文件服务层）
