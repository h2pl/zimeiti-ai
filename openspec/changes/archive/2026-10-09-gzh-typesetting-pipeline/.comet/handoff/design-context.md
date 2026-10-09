# Comet Design Handoff

- Change: gzh-typesetting-pipeline
- Phase: design
- Mode: compact
- Context hash: adbae3647afa5a7ae9358cbd2d172d194154d431caaf652fd97d30e9401e5812

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/gzh-typesetting-pipeline/proposal.md

- Source: openspec/changes/gzh-typesetting-pipeline/proposal.md
- Lines: 1-27
- SHA256: 7b6122cf634f7958f03e8e768b841a4bf7cf45b6cb8e285310de66c687b0e90a

```md
# Why

变更 real-account-verification（已归档）打通了双平台真实发布与读回 verified，但公众号发布质量存在明显短板：正文以裸 `<p>` 段落上送草稿箱，无排版、无代码高亮、无封面图——与手工运营的公众号文章（my-tools/wechat-mp-manage 产线：mistune 内联样式排版 + Pygments 代码高亮 + 主题封面）差距显著。公众号是首发平台之一，排版质量直接影响读者体验与账号专业度。需求来源：AGENTS.md 开发铁律「永远不要重复造轮子」（复用 my-tools 现成管线）+ 2026-10-09 real-account-verification 验证报告遗留项。

# What Changes

- vendor 复用 my-tools/wechat-mp-manage 排版三模块（上游未改动）：`md2html.py`（mistune + Pygments 内联样式转微信 HTML）、`formatting.py`（微信兼容内联样式/列表转 div/表格引用美化）、`generate_cover_combined.py`（Pillow 生成 2.35:1 + 1:1 拼接封面）
- 公众号发布链路升级：正文（Markdown）→ `convert_md_to_html` → `apply_wechat_styles` → 草稿箱 content；封面自动生成（标题取自草稿）并上传为 thumb
- 新增依赖：mistune、pygments、beautifulsoup4、Pillow
- 发布→读回 verified 闭环与频控/白名单护栏保持不变

# Capabilities

## Modified Capabilities

- `platform-publishing`：公众号发布需求升级——正文经排版管线转微信兼容 HTML、封面自动生成上传（MODIFIED，新增场景；读回对账/护栏行为不变）

## Added Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/vendor/wechatfmt/`（新增：上游三模块拷贝，标注来源）
- `apps/api/src/zimeiti_api/platforms/gzh.py`（发布前排版转换 + 封面生成接入）
- `apps/api/pyproject.toml`（新增 mistune/pygments/beautifulsoup4/pillow 依赖）
- 无数据库 schema 变更；无 API 面变更；xhs 侧不受影响

```

## openspec/changes/gzh-typesetting-pipeline/design.md

- Source: openspec/changes/gzh-typesetting-pipeline/design.md
- Lines: 1-64
- SHA256: 028e476d86317573e46df7959937d6d1b5c035fb8d9eb3bff6d24315e2cf7027

```md
---
comet_change: gzh-typesetting-pipeline
role: technical-design
canonical_spec: openspec
status: draft
---

# Design：gzh-typesetting-pipeline

## D0 复用策略（铁律：不重复造轮子）

排版能力完整复用 my-tools/wechat-mp-manage 上游实现，**vendor 拷贝而非重写**（与 real-account-verification 中 vendor wechat_mp 客户端同一模式）：

| vendor 模块 | 上游来源 | 用途 |
|---|---|---|
| `vendor/wechatfmt/md2html.py` | `my-tools/wechat-mp-manage/.../article_manage/md2html.py` | Markdown → 微信 HTML（mistune + Pygments monokai 内联高亮） |
| `vendor/wechatfmt/formatting.py` | 同上 `formatting.py` | 微信兼容内联样式（标题/段落/表格/引用/列表转 div） |
| `vendor/wechatfmt/generate_cover_combined.py` | 同上 `generate_cover_combined.py` | Pillow 拼接封面（2.35:1 + 1:1，标题自适应换行） |

上游文件保持一字未改（门禁 ruff/mypy/bandit/coverage 排除 vendor 目录，模式与 real-account-verification 一致）。选 vendor 而非 path 依赖/git 依赖：上游为个人私有仓、无包发布，且三模块零相互依赖、单文件自包含。

## D1 排版接入点

`platforms/gzh.py` 的 `publish_gzh_draft` 内、上送草稿箱前：

```
draft.body (Markdown)
  → convert_md_to_html(body)        # vendor md2html
  → apply_wechat_styles(html)      # vendor formatting，theme=ocean（上游默认）
  → articles[0]["content"]
```

替换现有 `f"<p>{draft.body}</p>"` 裸包裹。摘要（digest）沿用 `GzhDraft.summary`（模型生成），不移植 my-tools 的 `_extract_digest`（其输入是特定 Markdown 约定，模型直接产出摘要更可靠）。

## D2 封面生成

调用 vendored `generate_cover` 生成拼接封面 PNG（900×1283：上半 1:1、下半 2.35:1，微信上传后自动裁切）：

- `title` = 草稿标题；`sub`/`series` 传空——zimeiti-ai 无 my-tools 的系列体系（「AI Agent 学习+面试指南」为上游个人配置，不硬编码）
- 生成文件落 `data/outputs/gzh-main/<slug>/cover.png`
- 上传与 media_id 缓存复用沿用现有 `_DEFAULT_COVER_MEDIA_FILE` 机制，行为不变

## D3 依赖

新增（vendored 模块的直接依赖，全部为成熟库）：mistune（Markdown 解析）、pygments（代码高亮）、beautifulsoup4（formatting 的 DOM 处理）、Pillow（封面绘制）。

## D4 不做（Non-goals 落地）

- `content_wrapper.py`（结束语/最近文章/名片）与 `link_replacer.py`（已发布文章链接映射）：依赖 my-tools 个人系列配置与发布历史文件，zimeiti-ai 无对应体系——不移植，后续有需求单独立变更
- `trim_images.py`（正文图片裁剪）：当前草稿无正文图片场景
- xhs 侧任何改动

## D5 风险与对策

| 风险 | 对策 |
|---|---|
| 微信对 HTML 的兼容性差异（Tiptap/新版编辑器） | 管线在 my-tools 生产验证过（同一套内联样式上送草稿箱成功）；真账号走查 A3 复验 |
| 中文字体路径（封面绘制） | 沿用上游 `_find_font` 的多候选字体查找（Windows 含微软雅黑） |
| vendor 与上游漂移 | 门禁排除 vendor 目录；上游更新时重新拷贝覆盖（与 real-account-verification 模式一致） |

## D6 测试策略

- 单测：转换管线冒烟（代码块内联高亮/无 class/列表转 div）、发布 content 断言、封面 PNG 生成、失败路径
- 真账号走查：A3-gzh 复跑（发布带排版草稿到草稿箱 + 读回 verified + 公众号后台人工确认排版）

```

## openspec/changes/gzh-typesetting-pipeline/tasks.md

- Source: openspec/changes/gzh-typesetting-pipeline/tasks.md
- Lines: 1-14
- SHA256: b21c028837d101fc1afc49be69d9e5b24eeb00861214cf56e4f9413293efda00

```md
# Tasks

## 1. 管线接入

- [ ] 1.1 vendor 三模块：拷贝 my-tools/wechat-mp-manage 的 md2html.py/formatting.py/generate_cover_combined.py 至 vendor/wechatfmt/（标注来源，门禁排除配置），新增依赖 mistune/pygments/beautifulsoup4/pillow；验证：uv sync 通过 + 模块可导入 <!-- comet-task:eb3ad730-2be0-4368-b8fe-b6df362bc244 -->
- [ ] 1.2 发布链路接入：publish_gzh_draft 正文改走 convert_md_to_html + apply_wechat_styles，封面改走 generate_cover（title=草稿标题），摘要沿用 summary；验证：单测断言 content 含内联样式且无 class、thumb 走生成封面 <!-- comet-task:9f02a521-412d-4c5a-b4f9-96afd26103cc -->

## 2. 真账号走查

- [ ] 2.1 A3-gzh 复跑：发布带排版草稿至草稿箱 + 读回 verified + 公众号后台人工确认排版效果；验证：审计留痕 + 平台截图 <!-- comet-task:a71ab0d6-ff75-4669-af82-c300569392c0 -->

## 3. 收尾

- [ ] 3.1 验证报告增补（本轮缺陷与证据）；验证：文档与证据一致 <!-- comet-task:43318177-d347-4c16-8695-c9907fae35a5 -->

```

## openspec/changes/gzh-typesetting-pipeline/.openspec.yaml

- Source: openspec/changes/gzh-typesetting-pipeline/.openspec.yaml
- Lines: 1-2
- SHA256: 8ba8273010ceb66cd0ab320b2f49de179fac6fd6f648317c2cc129442eea7dc0

```md
schema: spec-driven
created: 2026-10-09

```

## openspec/changes/gzh-typesetting-pipeline/specs/platform-publishing/spec.md

- Source: openspec/changes/gzh-typesetting-pipeline/specs/platform-publishing/spec.md
- Lines: 1-29
- SHA256: 7c596ffa11b8871f40f63c22554b649f48c006c9fa0fe1edfa591ab50041d832

```md
# 平台发布（排版能力增量）

## ADDED Requirements

### Requirement: 公众号正文排版管线
公众号发布时，正文（Markdown）MUST 经排版管线转换为微信兼容 HTML 后再上送草稿箱：样式 MUST 全部内联（微信编辑器不支持 CSS class）、代码块 MUST 语法高亮、列表 MUST 转换为 div 结构（避免微信列表渲染异常）；转换 MUST 复用 my-tools/wechat-mp-manage 上游实现（vendor 引入并标注来源），禁止裸文本或未排版 HTML 直接上送。

#### Scenario: Markdown 正文转微信 HTML
- **GIVEN** 草稿正文为 Markdown（含标题、段落、代码块、列表）
- **WHEN** 公众号发布流程执行
- **THEN** 上送草稿箱的 content 为带内联样式的 HTML：代码块含深色背景与语法高亮、无 class 属性、列表为 div 结构

#### Scenario: 排版来源可审计
- **GIVEN** 排版管线由 my-tools/wechat-mp-manage 引入
- **WHEN** 检查 vendor 代码
- **THEN** 模块头部标注上游来源与改动说明，且与上游保持一字未改

### Requirement: 公众号封面自动生成
公众号发布时，系统 MUST 自动生成封面图（拼接规格：2.35:1 宽封面 + 1:1 方封面，标题取自草稿）并上传为草稿 thumb；未显式提供封面图时 MUST 自动生成而非留空；已上传的封面 media_id MUST 缓存复用以避免重复上传。

#### Scenario: 无显式封面时自动生成
- **GIVEN** 公众号发布流程启动且未提供封面图文件
- **WHEN** 执行发布
- **THEN** 系统生成拼接封面 PNG 并上传为 thumb_media_id，草稿携带该封面

#### Scenario: 封面缓存复用
- **GIVEN** 此前发布已上传过封面并缓存 media_id
- **WHEN** 后续发布未提供新封面图
- **THEN** 复用缓存的 thumb_media_id，不重复上传

```
