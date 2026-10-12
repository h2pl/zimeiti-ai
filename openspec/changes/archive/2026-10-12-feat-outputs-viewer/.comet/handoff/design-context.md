# Comet Design Handoff

- Change: feat-outputs-viewer
- Phase: design
- Mode: compact
- Context hash: 1f5761d36a8481d84eb443af41ae8ef8c8f6e62c5d16b6751a807f1d2429cd2c

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/feat-outputs-viewer/proposal.md

- Source: openspec/changes/feat-outputs-viewer/proposal.md
- Lines: 1-30
- SHA256: 761e434bd3ac9f44bdaac921286dd37567a135c07e0e5ed8abef5b78950127c2

```md
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

```

## openspec/changes/feat-outputs-viewer/design.md

- Source: openspec/changes/feat-outputs-viewer/design.md
- Lines: 1-24
- SHA256: 9b13f2b3aff469100e07487aeaf43e5a1f1d4639095eda599557536a08e9e115

```md
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

```

## openspec/changes/feat-outputs-viewer/tasks.md

- Source: openspec/changes/feat-outputs-viewer/tasks.md
- Lines: 1-6
- SHA256: 0ac86adcebb10c8648f43ded26060fa746c93f97ac649799a4185f7fe7a4e5cf

```md
# 任务：feat-outputs-viewer

- [ ] T1 `workbench.output_detail()` + GET /api/outputs/{account}/{slug} 端点
      （404/400 防护）+ 测试
- [ ] T2 OutputsPage 行点击查看器（modal + marked 渲染双平台正文）
- [ ] T3 make check + pnpm build + spec 场景核对（含路径遍历拒绝）

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
- SHA256: 0c9af2dada9cfd9221b965905f90458e8814287aa2a7e3ffd4d0aae1f682d16d

```md
# web-workbench 能力增量（feat-outputs-viewer）

## ADDED Requirements

### Requirement: 内容正文查看器

OutputsPage 支持点开单篇产物查看：标题、账号、创建时间、合规结论、双平台
草稿正文（markdown 渲染）。数据来自 `GET /api/outputs/{account}/{slug}`
（只读，account/slug 经白名单校验，非法输入 400，不存在 404）。

#### Scenario: 查看已有草稿正文
- **When** 点击内容库某一行
- **Then** 查看器渲染该 slug 的 xhs/gzh 双平台正文（markdown 转 HTML 经 DOMPurify 消毒）

#### Scenario: 非法 slug 被拒绝
- **When** GET /api/outputs/xhs-main/..%2Fetc
- **Then** 返回 400 或 404，不返回任何文件内容

```
