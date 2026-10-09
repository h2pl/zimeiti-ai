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
