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
