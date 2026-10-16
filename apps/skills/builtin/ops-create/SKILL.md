---
name: ops-create
description: >-
  运营制作层路由：按画像写成稿并质检。当用户说「写文章、出初稿、做内容、写成稿」
  时使用。本层是路由层——执行时先读下方详细技能。
layer: produce
---

# ops-create 制作层（路由）

## 触发

写文章 / 出初稿 / 做内容 / 写成稿 / 润色

## 必读详细技能（按任务精度选，先读再执行）

- `skills/builtin/copywriting/SKILL.md`：文案写作（长文/短文案/润色/去 AI 味）
- `skills/builtin/skill-quality-gate/SKILL.md`：交付前质量门（AI 味/合规/规格自检）
- `skills/builtin/skill-article-outline/SKILL.md`：长文大纲构建

## 本层职责与产物

凝练画像制作相关维度（identity/style/audience/preferences；**制作层不读 platforms.md**），
按写作规范产出成稿。产物：`outputs/<主题项目名>/` 下的 Markdown（路径先经
output_paths.py 校验；主题禁泛名）。

## 脚本化质检（exec_script 调用）

- `ai_score`（位置参数=文章路径）：AI 味/质量评分，🟢 PASS 再交付
- `content_guard`（子命令 `scan`，`--file` 文章路径）：出站前敏感信息扫描，
  BLOCK 级命中（退出码 7）必须改稿

## 交接

成稿交给发布层（ops-publish）排版上传，或归因层留档。
