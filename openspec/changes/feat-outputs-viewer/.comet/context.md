# Comet Design Handoff

- Change: feat-outputs-viewer
- Phase: design
- Mode: compact
- Context hash: 6865e5fad6bb4231157beb820fb5a4794bb1cae88546766c35ecf9f39dfc41f5

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/feat-outputs-viewer/proposal.md

- Source: openspec/changes/feat-outputs-viewer/proposal.md
- Lines: 1-28
- SHA256: cfacf838f50675704e79c72bf22f6148dc9e12f993fd694e1fa0b005e51984ef

```md
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

```

## openspec/changes/feat-outputs-viewer/design.md

- Source: openspec/changes/feat-outputs-viewer/design.md
- Lines: 1-17
- SHA256: 55678f5c7d9051a0317218ea10e5d9f1280a688ccdd2f8beb772edce1ca84bfc

```md
---
comet_change: feat-outputs-viewer
role: technical-design
canonical_spec: openspec
---

# 设计：feat-outputs-viewer

## 决策记录

- **D1 单篇产物读取**：`operations/workbench.py` 增 `output_detail(account, slug,
  outputs_dir)`——白名单校验 + 读 `OUTPUTS_DIR/<account>/<slug>/drafts.json`
  全量返回（正文是产物本体，量可控，不裁剪）。
- **D2 封面图**：端点直接 `FileResponse`（cover.png 存在判定；不存在 404）。
  路径拼接全部用 Path + 白名单，防 `../` 穿越。
- **D3 前端**：OutputsPage 条目展开面板（标题/正文/封面 + 合规徽章），
  api.ts 增 fetchOutputDetail / coverUrl helper。

```

## openspec/changes/feat-outputs-viewer/tasks.md

- Source: openspec/changes/feat-outputs-viewer/tasks.md
- Lines: 1-6
- SHA256: a7de2805b79b944fe3a8ad216a7e3d9cb5894d9deb4060d8fb8ff7613d5537ff

```md
# 任务：feat-outputs-viewer

- [ ] T1 后端：output_detail + GET /api/outputs/{account}/{slug} + cover.png
      FileResponse + 测试（含 404/400 路径穿越）
- [ ] T2 前端：OutputsPage 展开正文面板 + 封面图
- [ ] T3 make check + npm build + spec 场景核对

```

## openspec/changes/feat-outputs-viewer/.openspec.yaml

- Source: openspec/changes/feat-outputs-viewer/.openspec.yaml
- Lines: 1-2
- SHA256: 1dfdca412094f24473d8b842866201ec26f200b29b17064b03f1e4982c35a7b9

```md
schema: spec-driven
created: 2026-10-12

```

## openspec/changes/feat-outputs-viewer/specs/web-workbench/spec.md

- Source: openspec/changes/feat-outputs-viewer/specs/web-workbench/spec.md
- Lines: 1-17
- SHA256: fc308a975e531d6347f85e2736fa27f237499fb3988c37afa0bc44abf0763b4b

```md
# web-workbench 能力增量（feat-outputs-viewer）

## ADDED Requirements

### Requirement: 内容库正文查看

`GET /api/outputs/{account}/{slug}` 返回单篇产物全文（选题/方向/合规结论/
两平台草稿全文 + created_at）；`GET /api/outputs/{account}/{slug}/cover.png`
以 FileResponse 返回封面图（存在时）。参数白名单防路径遍历；不存在 404。

#### Scenario: 展开正文
- **When** 用户在内容库展开某条目
- **Then** 页面展示两平台标题正文与封面图（若有）

#### Scenario: 非法 slug 拒绝
- **When** slug 含路径分隔符
- **Then** 返回 400

```
