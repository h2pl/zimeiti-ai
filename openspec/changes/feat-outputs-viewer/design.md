---
comet_change: feat-outputs-viewer
role: technical-design
canonical_spec: openspec
---

# 设计：feat-outputs-viewer

## Context

OutputsPage 现仅元数据列表（workbench.outputs 扫 drafts.json 摘要）。发布编排
（下一变更）需要先看到内容。Easel OutputsPage 的「查看文章」交互为对标物。

## 决策记录

- **D1 端点**：`GET /api/outputs/{account}/{slug}` →
  `operations/workbench.py` 增 `output_detail(account, slug, outputs_dir)`：
  复用 valid_account 白名单 + slug 白名单（同 regex），读 drafts.json 返回
  {slug, account, topic, created_at, compliance, drafts}（drafts 含 xhs/gzh
  正文）。不存在 404。
- **D2 前端**：OutputsPage 行点击打开侧滑查看器（复用 overlay/modal 体系）；
  正文经 marked+DOMPurify 渲染（依赖已就绪，不新增）。
- **D3 安全**：slug 白名单正则同 account（`^[A-Za-z0-9_-]+$`），杜绝
  `..%2F` 路径遍历；只读端点。
