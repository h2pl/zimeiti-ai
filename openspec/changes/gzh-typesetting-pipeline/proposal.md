# Why

变更 real-account-verification（已归档）打通了双平台真实发布与读回 verified，其 build 阶段已接入正文排版转换（vendor md2html + formatting，mistune 内联样式 + Pygments 高亮）。遗留缺口：**封面仍是纯色占位 PNG 或复用旧 media_id**，与手工运营的公众号文章（my-tools/wechat-mp-manage 产线的主题拼接封面：2.35:1 宽封面 + 1:1 方封面、标题自适应排版）差距显著。封面是公众号文章的门面，直接影响读者体验与账号专业度。需求来源：AGENTS.md 开发铁律「永远不要重复造轮子」（复用 my-tools 现成管线）+ 2026-10-09 real-account-verification 验证报告遗留项。

# What Changes

- vendor 复用 my-tools/wechat-mp-manage 封面模块（上游未改动）：`generate_cover_combined.py`（Pillow 生成 2.35:1 + 1:1 拼接封面，标题自适应排版）
- 公众号发布链路补齐：无显式封面时自动生成拼接封面（标题取自草稿，系列名/子分类留空）并上传为 thumb，裁剪坐标随草稿上送
- 正文排版转换（md2html + formatting）已由前一变更落地，本变更不含
- 新增依赖：Pillow
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
